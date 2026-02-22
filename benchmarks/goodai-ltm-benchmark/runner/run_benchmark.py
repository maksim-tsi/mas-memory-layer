# mypy: ignore-errors

import logging
import os
import os.path
import re
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import IO

import click
import yaml
from dataset_interfaces.factory import DATASETS, DatasetFactory
from dataset_interfaces.interface import TestExample
from model_interfaces.cost_estimation import CostEstimationChatSession
from model_interfaces.gemini_interface import GeminiProInterface
from model_interfaces.groq_interface import GroqChatSession
from model_interfaces.huggingface_interface import HFChatSession
from model_interfaces.human import HumanChatSession
from model_interfaces.interface import ChatSession
from model_interfaces.length_bias_agent import LengthBiasAgent
from model_interfaces.llm_interface import LLMChatSession, TimestampLLMChatSession
from model_interfaces.mas_agents import MASFullContextSession, MASFullSession, MASRAGSession
from model_interfaces.mistral_interface import MistralChatSession
from model_interfaces.remote_agent import RemoteMASAgentSession
from utils.constants import MAIN_DIR, TESTS_DIR
from utils.files import (
    gather_persistence_files,
    gather_result_files,
    gather_testdef_files,
    make_config_path,
    make_run_path,
)
from utils.llm import GPT_4_TURBO_BEST
from utils.ui import ask_yesno, colour_print

from runner.config import RunConfig
from runner.run_manifest import RunManifest
from runner.scheduler import TestRunner
from runner.stuck_watchdog import StuckWatchdog
from runner.turn_metrics import TurnMetricsWriter


class _TeeWriter:
    def __init__(self, *streams: IO[str]) -> None:
        self._streams = streams

    def write(self, data: str) -> int:
        written = 0
        for stream in self._streams:
            written = stream.write(data)
        return written

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


def get_chat_session(
    name: str, max_prompt_size: int | None, run_name: str, is_local=False
) -> ChatSession:
    kwargs = {"max_prompt_size": max_prompt_size} if max_prompt_size is not None else {}
    kwargs["run_name"] = run_name
    kwargs["is_local"] = is_local

    if name == "gemini":
        return GeminiProInterface(run_name=run_name)
    if name == "groq":
        return GroqChatSession(run_name=run_name)
    if name == "mistral":
        return MistralChatSession(run_name=run_name)

    if name == "mas-full":
        return MASFullSession(**kwargs)

    if name == "mas-rag":
        return MASRAGSession(**kwargs)

    if name == "mas-full-context":
        return MASFullContextSession(**kwargs)

    if name == "mas-remote":
        return RemoteMASAgentSession(**kwargs)

    if name.startswith("ltm_agent_"):
        from model_interfaces.ltm_agent_wrapper import LTMAgentVariant, LTMAgentWrapper

        match = re.match(r"^ltm_agent_(?P<variant>\d)(?:\((?P<model>.+)\))?$", name)
        if match is None:
            raise ValueError(f"Unrecognized LTM Agent {name!r}.")
        params = match.groupdict()
        model = params["model"] or GPT_4_TURBO_BEST
        variant = {
            "1": LTMAgentVariant.QG_JSON_USER_INFO,
            "2": LTMAgentVariant.SEMANTIC_ONLY,
            "3": LTMAgentVariant.TEXT_SCRATCHPAD,
        }.get(params["variant"])
        if variant is None:
            raise ValueError(f"Unrecognized LTM Agent variant {params['variant']!r}.")
        return LTMAgentWrapper(model=model, variant=variant, **kwargs)
    if name == "length_bias":
        return LengthBiasAgent(model=GPT_4_TURBO_BEST, **kwargs)
    if name.startswith("cost("):
        in_cost, out_cost = (
            float(p.strip()) / 1_000
            for p in name.removeprefix("cost(").removesuffix(")").split(",")
        )
        return CostEstimationChatSession(cost_in_token=in_cost, cost_out_token=out_cost, **kwargs)
    if name == "human":
        return HumanChatSession(**kwargs)
    if name.startswith("huggingface/"):
        kwargs.pop("is_local")
        return HFChatSession(model=name, **kwargs)

    try:
        cls = TimestampLLMChatSession if name.startswith("ts-") else LLMChatSession

        return cls(model=name.removeprefix("ts-"), **kwargs)
    except ValueError:
        pass

    raise ValueError(f"Unrecognized agent: {name}")


def generate_test_examples(
    loaded_yaml, max_message_size: int, pass_default: bool = False, force_regenerate: bool = False
) -> list[TestExample]:
    run_name = loaded_yaml["config"]["run_name"]
    test_definitions = gather_testdef_files(run_name)

    if len(test_definitions) > 0:
        if not force_regenerate:
            if pass_default or ask_yesno(
                f"There are test definitions in disk for run name {run_name}",
                question="Do you want to reuse these test definitions?",
            ):
                return load_test_examples(loaded_yaml, test_definitions)
            if not ask_yesno(
                "WARNING: overwriting the test definitions will result in the loss of all "
                "results associated with them, including those from other agents.",
                default_yes=False,
            ):
                raise ValueError("Run aborted")
        shutil.rmtree(make_run_path(run_name))

    # Save original yaml configuration
    config_path = make_config_path(run_name)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as file:
        yaml.safe_dump(loaded_yaml, file)

    examples: list[TestExample] = []
    dataset_yaml = loaded_yaml["datasets"]
    for ds in dataset_yaml["datasets"]:
        examples.extend(DatasetFactory.create_examples(ds, dataset_yaml["args"], max_message_size))

    for example in examples:
        example.save(run_name)

    return examples


def load_test_examples(yaml_configuration, test_definition_paths: list[str]) -> list[TestExample]:
    examples = []
    for p in test_definition_paths:
        dataset = DatasetFactory.create_dataset_for_example(yaml_configuration, p)
        examples.append(TestExample.load(dataset, p))

    return examples


def load_examples_from_dir(dataset_path: str, yaml_configuration: dict) -> list[TestExample]:
    path = Path(dataset_path)
    if not path.exists():
        raise ValueError(f"Dataset path {dataset_path} does not exist.")

    # Recursively find .def.json files
    test_definition_paths = [str(p) for p in path.glob("**/*.def.json")]
    print(f"Loading {len(test_definition_paths)} tests from {dataset_path}")
    return load_test_examples(yaml_configuration, test_definition_paths)


def check_result_files(
    run_name: str, agent_name: str, force_removal: bool = False, pass_default: bool = False
):
    result_files = gather_result_files(run_name, agent_name)
    persistence_files = gather_persistence_files(run_name, agent_name)
    all_files = result_files + persistence_files
    resume = False
    if force_removal:
        for file in all_files:
            os.remove(file)
        all_files = []
    if all_files and not pass_default:
        if not ask_yesno(
            f"There are {len(all_files)} existing file that have been found for run name '{run_name}' "
            f"and agent '{agent_name}'.",
            question="Do you want to resume the run?",
        ):
            if not ask_yesno(
                "ALL RESULT FILES WILL BE LOST for the current run name and agent.",
                default_yes=False,
            ):
                colour_print("red", "Run aborted.")
                exit()
            for file in all_files:
                os.remove(file)
            resume = False
        else:
            resume = True
    return resume


@click.command("run-benchmark")
@click.option(
    "-c",
    "--configuration",
    required=False,
    type=str,
    default="./configurations/benchmark_1.yml",
)
@click.option("-a", "--agent-name", required=True, type=str)
@click.option("-m", "--max-prompt-size", required=False, type=int, default=None)
@click.option(
    "-y", required=False, is_flag=True, default=False, help="Automatically assent to questions"
)
@click.option(
    "-l",
    "--local",
    required=False,
    is_flag=True,
    default=False,
    help="Do not try to retrieve costs.",
)
@click.option(
    "-i",
    "--isolated",
    required=False,
    is_flag=True,
    default=False,
    help=("Run tests separately, without interleaving and clearing up the context between tests."),
)
@click.option("--run-name", required=False, type=str, default=None)
@click.option("--run-id", required=False, type=str, default=None)
@click.option(
    "--progress",
    required=False,
    type=click.Choice(["tqdm", "tk", "none"], case_sensitive=False),
    default="tqdm",
)
@click.option("--stuck-timeout", required=False, type=int, default=15)
@click.option("--turn-metrics/--no-turn-metrics", default=True)
@click.option("--metrics-sample-rate", required=False, type=float, default=1.0)
@click.option("--test-filter", required=False, type=str, default=None)
@click.option("--dataset-path", required=False, type=str, default=None)
def main(
    configuration: str,
    agent_name: str,
    max_prompt_size: int | None,
    y: bool = False,
    local: bool = False,
    isolated: bool = False,
    run_name: str | None = None,
    run_id: str | None = None,
    progress: str = "tqdm",
    stuck_timeout: int = 15,
    turn_metrics: bool = True,
    metrics_sample_rate: float = 1.0,
    test_filter: str | None = None,
    dataset_path: str | None = None,
):
    _main(
        configuration,
        agent_name,
        max_prompt_size,
        y,
        local,
        isolated,
        run_name,
        run_id,
        progress,
        stuck_timeout,
        turn_metrics,
        metrics_sample_rate,
        test_filter,
        dataset_path,
    )


def _main(
    configuration: str,
    agent_name: str,
    max_prompt_size: int | None,
    y: bool = False,
    is_local: bool = False,
    isolated: bool = False,
    run_name: str | None = None,
    run_id: str | None = None,
    progress: str = "tqdm",
    stuck_timeout: int = 15,
    turn_metrics: bool = True,
    metrics_sample_rate: float = 1.0,
    test_filter: str | None = None,
    dataset_path: str | None = None,
):
    progress = progress.lower()
    config_path = Path(configuration)
    if not config_path.is_absolute():
        config_path = MAIN_DIR.joinpath(configuration)
    with open(config_path, "rb") as file:
        loaded_yaml = yaml.safe_load(file)

    yaml_config = loaded_yaml["config"]
    if run_name:
        yaml_config["run_name"] = run_name
    config = {k: v for k, v in yaml_config.items() if k != "incompatibilities"}
    incompatibilities = []
    for inc_list in yaml_config.get("incompatibilities", []):
        incompatibilities.append({DATASETS[ds_name] for ds_name in inc_list})
    conf = RunConfig(
        incompatibilities=incompatibilities,
        isolated=isolated,
        run_id=run_id or _default_run_id(yaml_config["run_name"]),
        progress=progress,
        stuck_timeout_minutes=stuck_timeout,
        turn_metrics=turn_metrics,
        metrics_sample_rate=metrics_sample_rate,
        **config,
    )
    if isolated:
        new_run_name = f"{conf.run_name} (isolated)"
        new_def_path = TESTS_DIR.joinpath(new_run_name, "definitions")
        if not new_def_path.exists():
            shutil.copytree(TESTS_DIR.joinpath(conf.run_name, "definitions"), new_def_path)
        conf.run_name = new_run_name
    if max_prompt_size is None:
        logging.warning("Running without a maximum prompt size.")
    else:
        print(f"Maximum prompt size: {max_prompt_size}")

    agent = get_chat_session(
        agent_name, max_prompt_size=max_prompt_size, run_name=config["run_name"], is_local=is_local
    )

    if dataset_path:
        examples = load_examples_from_dir(dataset_path, loaded_yaml)
    else:
        examples = generate_test_examples(loaded_yaml, agent.max_message_size, pass_default=y)
    examples = _apply_test_filter(examples, test_filter)
    resume = check_result_files(conf.run_name, agent.name, pass_default=y)
    if resume:
        agent.load()

    run_path = make_run_path(conf.run_name, agent.name)
    run_path.mkdir(parents=True, exist_ok=True)
    console_log_path = run_path.joinpath("run_console.log")
    log_handle = console_log_path.open("a", encoding="utf-8")
    log_handler = logging.StreamHandler(log_handle)
    log_handler.setLevel(logging.INFO)
    log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(log_handler)
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = _TeeWriter(original_stdout, log_handle)
    sys.stderr = _TeeWriter(original_stderr, log_handle)
    metrics_writer = None
    if conf.turn_metrics:
        metrics_writer = TurnMetricsWriter(
            run_path.joinpath("turn_metrics.jsonl"), sample_rate=conf.metrics_sample_rate
        )
    run_manifest = RunManifest.start(
        run_id=conf.run_id,
        run_name=conf.run_name,
        agent_name=agent.name,
        config_path=str(config_path),
        progress=conf.progress,
        stuck_timeout_minutes=conf.stuck_timeout_minutes,
        turn_metrics=conf.turn_metrics,
        metrics_sample_rate=conf.metrics_sample_rate,
    )
    run_manifest.write(run_path.joinpath("run_meta.json"))

    stuck_watchdog = StuckWatchdog(
        timeout=timedelta(minutes=conf.stuck_timeout_minutes),
        run_error_path=run_path.joinpath("run_error.json"),
    )

    runner = TestRunner(
        config=conf, agent=agent, tests=examples, skip_evaluations=agent_name.startswith("cost(")
    )
    runner.run_id = conf.run_id
    runner.metrics_writer = metrics_writer
    runner.stuck_watchdog = stuck_watchdog
    time1 = time.time()
    try:
        runner.run()
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        logging.getLogger().removeHandler(log_handler)
        log_handle.close()
        run_manifest.finish()
        run_manifest.write(run_path.joinpath("run_meta.json"))

    time2 = time.time()
    elapsed = (time2 - time1) / 60
    colour_print("green", f"Done in {elapsed:.2g} minutes.")


def _default_run_id(run_name: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{run_name}_{stamp}".replace(" ", "_")


def _apply_test_filter(examples: list[TestExample], test_filter: str | None) -> list[TestExample]:
    if not test_filter:
        return examples
    dataset = ""
    example_id = ""
    if ":" in test_filter:
        dataset, example_id = test_filter.split(":", 1)
    elif "/" in test_filter:
        dataset, example_id = test_filter.split("/", 1)
    else:
        dataset = test_filter
    dataset = dataset.strip()
    example_id = example_id.strip()
    filtered: list[TestExample] = []
    for example in examples:
        if dataset and example.dataset_name != dataset:
            continue
        if example_id and str(example.example_id) != example_id:
            continue
        filtered.append(example)
    if not filtered:
        raise ValueError(f"No tests matched filter {test_filter!r}.")
    return filtered


if __name__ == "__main__":
    main()
