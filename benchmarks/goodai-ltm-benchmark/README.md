# GoodAI LTM Benchmark

![GoodAI Logo. A cybernetic owl, which is half robot, half organic, and next to it the company name: GoodAI](reporting/templates/GoodAI_logo.png "GoodAI Research s.r.o.")

This repository contains the code and data to replicate our experiments regarding the Long-Term Memory (LTM) abilities of conversational agents. The benchmark was originally released jointly with [a blogpost](https://www.goodai.com/introducing-goodai-ltm-benchmark/), check it out for obtaining more information about the benchmark and the related research goals.

As part of our research efforts in the area of continual learning, we are open-sourcing this benchmark for testing agents’ ability to perform tasks involving the advanced use of the memory over very long conversations. Among others, we evaluate the agent’s performance on tasks that require dynamic upkeep of memories or integration of information over long periods of time.

We are open-sourcing:
 * The living GoodAI LTM Benchmark (this repository).
 * Our [LTM agents](model_interfaces/).
 * Our experiment [data](data/tests/Benchmark%202%20-%2010k%20Filler/definitions) and [results](data/tests/Benchmark%202%20-%2010k%20Filler/results).

## MAS Memory Layer Modifications

This repository is maintained as an **improved, MAS-integrated version** of the GoodAI LTM Benchmark. The original benchmark methodology and evaluation datasets remain unchanged to preserve academic rigor, while operational tooling has been enhanced for modern MAS workflows.

**Key improvements:**
- **Gemini provider**: The default evaluation model is Google Gemini (e.g., `gemini-2.5-flash-lite`) rather than OpenAI GPT-4.
- **Enhanced visibility**: Headless-friendly progress reporting and structured telemetry are being added to improve run transparency.
- **Static typing hardening**: The benchmark package has been aligned with the repository's strict mypy configuration through typed interfaces and Optional guards.

**Historical results disclaimer:**
Historical benchmark results produced using OpenAI GPT-4 are **not directly comparable** to our current runs. The benchmark protocol and evaluation data are unchanged, but the model family and inference characteristics differ.

See the following documents for current transparency analysis and the implementation plan:
- [Visibility Analysis](docs/visibility-analysis.md)
- [Visibility Improvement Plan](docs/improvement-plan.md)

## Running the Benchmarks

These tests require Python 3.11 or higher.

### Local Execution

First, set your `GOOGLE_API_KEY` environment variable and install dependencies:
```bash
cd benchmarks/goodai-ltm-benchmark
poetry install
```

**CRITICAL:** Execute benchmark as a module (not as script path) to avoid package name collision with HuggingFace `datasets`:

```bash
# Correct (module execution)
poetry run python -m runner.run_benchmark \
  -c configurations/published_benchmarks/<configuration_name>.yml \
  -a gemini -m 4096

# WRONG (will fail with "No module named 'datasets.instruction_recall'")
python runner/run_benchmark.py -c ...
```

### Docker Execution (Recommended for MAS Agents)

For benchmarking MAS memory agents via the wrapper service:

```bash
# From repository root
cd /path/to/mas-memory-layer

# Build containers
docker-compose build benchmark-runner mas-agent

# Start services
docker-compose up -d

# Execute benchmark
docker exec -w /app mas-memory-layer-benchmark-runner-1 \
  python -m runner.run_benchmark \
  -c configurations/mas_remote_test.yml \
  -a mas-remote
```

For a quick 5-task smoke run (5 datasets x 1 example), you can use:

```bash
python -m runner.run_benchmark -c configurations/mas_variant_a_smoke_5.yml -a mas-remote
```

**Docker Architecture:**
- `mas-agent`: FastAPI wrapper exposing MAS memory system (L1-L4)
- `benchmark-runner`: Isolated benchmark environment with all datasets
- Communication: HTTP via `AGENT_URL` env var (default: `http://mas-agent:8080/v1/chat/completions`)

### Output

This will generate a set of test specifications if there is not one already, and start to produce result files, one for each test. The result files will be located at `./data/tests/<benchmark_name>/results/<agent_name>/`.

At the end of testing, an HTML report will be generated in `data/reports` which will give a detailed breakdown of the tests run, responses, and evaluations. It will be given a name of the form `<time stamp> - Detailed Report - <run_name> - <agent_name>.html`.

## Agents

The agents that have been specifically implemented in this repository are the ones shown below. For implementing your own agent, please see the more detailed instructions [here](model_interfaces/README.md).

```text
# Google Gemini
gemini-2.5-flash-lite  # Gemini 2.5 Flash Lite (native google-genai)

# Legacy identifiers (not active in the native Gemini-only integration)
gpt-3.5-turbo
gpt-4-turbo
gpt-4o
claude-2.1
claude-3-haiku
claude-3-sonnet
claude-3-opus

# Google Gemini (legacy)
gemini                 # Gemini 1.5 Pro

# Models with timestamped messages
ts-<model>          # Any of the above models

# GoodAI LTM models
# Variants:
#   1. semantic retrieval + query generation + JSON scratchpad
#   2. semantic retrieval
#   3. semantic retrieval + text scratchpad
# Optional model ID to use as core LLM
# Example: ltm_agent_1(claude-3-opus-20240229)
ltm_agent_<variant>[(<model>)]

# MAS Memory Layer Agents (Docker-based)
mas-full          # Full 4-tier memory system (L1-L4)
mas-rag           # RAG-only variant (L3: Qdrant + Neo4j)
mas-full-context  # Full context baseline (no memory)
mas-remote        # HTTP wrapper to FastAPI agent service

# Cost Estimation
cost(<cost_in_tokens>,<cost_out_tokens>) # Model for estimating the cost of a 
                                           benchmark based on the input and output
                                           costs

# Human models
human             # A CLI interface for a human to use the tests.
```

**Note on MemGPT Baseline:** The `memgpt` agent identifier has been suspended as of 2026-02-10 due to removal of the `pymemgpt` dependency (enforced Python `<3.13` constraint). See [docs/pymemgpt-analysis.md](docs/pymemgpt-analysis.md) for migration path to Letta if MemGPT comparisons are required.

## Native Gemini Provider

This benchmark uses the native Google Gemini client (`google-genai`) rather than the litellm abstraction. The default evaluation model is `gemini-2.5-flash-lite`, and the runtime enforces a conservative context budget of 96k tokens per call (configurable via `MAS_GEMINI_MAX_CONTEXT_TOKENS`). Usage metadata is collected from Gemini responses for cost and throughput tracking, and token usage is emitted at debug log level for traceability.


## Configurations

The configuration files used in the different versions of the benchmark can be found in `configurations/published_benchmarks`, in which `<x>k` denotes the memory span in thousands of tokens. For each of the benchmarks under a single version, we keep the scripts and needles the same, but we increase the amount of filler tokens owing to the larger memory span. Older configurations from previous releases can be found in `published_benchmarks/legacy`. These configuration files are compatible only with their corresponding releases and their operation is described in the readmes for those releases.


## Datasets

The datasets that are implemented for this benchmark can be found in `./datasets/`. Briefly, they are:

```
chapterbreak
colours
jokes
locations_directions
name_list
prospective_memory
restaurant
sallyanne
shopping
spy_meeting
trigger_response
```

More details for each of the tests can be found from their descriptions inside each of their individual files.

## Technical Details

The repository consists of four parts:

- **Datasets:** These are test generators, either through random combination of words, phrases, and numbers, sampling lines from an existent dataset, or generating them via a prompted GPT.
- **Models:** A model is an agent that can be set to perform the tasks of the dataset. This part presents a very simple interface and facilitates the integration of agents with the benchmark.
- **Runner:** This script takes a configuration and model specification, optionally generates the set of test instances, and executes the benchmark.
- **Reports:** These files generate the reports as self-contained HTML files, with support for individual and comparative reporting. 

More details for each of these parts can be found here: [datasets](datasets/README.md), [models](model_interfaces/README.md), [runner](runner/README.md), [reports](reporting/README.md).


## Benchmark 3.5 - 06/2024

### Benchmark 3 - Isolated (No Memory Span)

| Model                      | Context Tokens | Score / 11 | Time (m) | Cost ($) |
|----------------------------|---------------:|-----------:|---------:|---------:|
| Mixtral-8x7B Instruct 0.1  |          32768 |          5 |    10.25 |     0.15 | 
| Mixtral-8x22B Instruct 0.1 |          65536 |        4.9 |       11 |     0.61 |
| Llama 3 70B Instruct       |           8000 |        8.2 |      8.8 |     0.13 | 
| GPT-3.5-turbo              |          16384 |        4.1 |        6 |     0.13 | 
| GPT-4 Turbo                |         128000 |        7.9 |     18.5 |     6.94 | 
| GPT-4o                     |         128000 |        7.6 |        8 |     3.08 | 
| Claude 3 Opus              |         200000 |        8.3 |       41 |    15.28 | 
| Gemini 1.5 Pro             |        2000000 |        7.4 |       58 |      --- |
| LTMAgent 1 (Llama 3 70B)   |           8000 |        8.4 |       26 |     0.65 |
| LTMAgent 1 (GPT-4-turbo)   |          16384 |        9.2 |     68.3 |     9.81 |
| LTMAgent 1 (Claude)        |          16384 |        8.7 |     99.5 |     0.52 | 


### Benchmark 3 - 2k Memory Span (Without ChapterBreak)

| Model                      | Context Tokens | Score / 10 | Time (m) | Cost ($) |
|----------------------------|---------------:|-----------:|---------:|---------:|
| Mixtral-8x7B Instruct 0.1  |          32768 |        1.4 |      7.5 |     0.08 | 
| Mixtral-8x22B Instruct 0.1 |          65536 |        5.6 |     97.2 |     0.93 |
| Llama 3 70B Instruct       |           8000 |        1.9 |      4.5 |     0.08 | 
| GPT-3.5-turbo              |          16384 |        4.7 |      8.1 |     0.31 | 
| GPT-4 Turbo                |         128000 |        6.6 |      5.5 |     8.29 | 
| GPT-4o                     |         128000 |        5.9 |      4.8 |     4.55 | 
| Claude 3 Opus              |         200000 |        7.8 |     41.8 |    19.19 | 
| Gemini 1.5 Pro             |        2000000 |        6.5 |       55 |      --- |
| LTMAgent 1 (Llama 3 70B)   |           8000 |        6.9 |     22.9 |      1.2 |
| LTMAgent 1 (GPT-4-turbo)   |          16384 |        6.3 |       99 |    17.34 |
| LTMAgent 1 (Claude)        |          16384 |        7.5 |     90.8 |     0.38 | 



### Benchmark 3 - 32k Memory Span

| Model                      | Context Tokens | Score / 11 | Time (m) | Cost ($) |
|----------------------------|---------------:|-----------:|---------:|---------:|
| Mixtral-8x7B Instruct 0.1  |          32768 |        0.1 |        9 |     0.06 | 
| Mixtral-8x22B Instruct 0.1 |          65536 |        0.0 |       18 |     0.93 |
| Llama 3 70B Instruct       |           8000 |        0.2 |     10.8 |     0.06 | 
| GPT-3.5-turbo              |          16384 |        0.1 |      5.5 |     0.06 | 
| GPT-4 Turbo                |         128000 |        4.8 |     18.5 |    77.74 | 
| GPT-4o                     |         128000 |        4.6 |       15 |    38.38 | 
| Claude 3 Opus              |         200000 |        6.7 |    133.5 |   215.42 | 
| Gemini 1.5 Pro             |        2000000 |        6.4 |       39 |      --- |
| LTMAgent 1 (Llama 3 70B)   |           8000 |          5 |     43.7 |     2.50 |
| LTMAgent 1 (GPT-4-turbo)   |          16384 |        5.2 |    171.9 |    61.46 |
| LTMAgent 1 (Claude)        |          16384 |          5 |    173.2 |     0.68 | 


### Benchmark 3 - 120k Memory Span

| Model                      | Context Tokens | Score / 11 | Time (m) | Cost ($) |
|----------------------------|---------------:|-----------:|---------:|---------:|
| Mixtral-8x7B Instruct 0.1  |          32768 |        0.1 |      7.7 |     0.06 | 
| Mixtral-8x22B Instruct 0.1 |          65536 |        0.1 |     21.1 |     1.12 |
| Llama 3 70B Instruct       |           8000 |        0.2 |      9.4 |     0.06 | 
| GPT-3.5-turbo              |          16384 |        0.0 |        6 |     1.33 | 
| GPT-4 Turbo                |         128000 |        5.8 |       49 |   215.86 | 
| GPT-4o                     |         128000 |        5.5 |       32 |   108.22 | 
| Claude 3 Opus              |         200000 |        7.4 |      519 |   476.68 | 
| Gemini 1.5 Pro             |        2000000 |        7.0 |      --- |      --- |
| LTMAgent 1 (Llama 3 70B)   |           8000 |        4.7 |     86.5 |     3.10 |
| LTMAgent 1 (GPT-4-turbo)   |          16384 |        5.0 |    567.5 |    89.36 |
| LTMAgent 1 (Claude)        |          16384 |        5.7 |    307.5 |   158.24 | 


### Benchmark 3 - 200k Memory Span

| Model                      | Context Tokens | Score / 11 | Time (m) | Cost ($) |
|----------------------------|---------------:|-----------:|---------:|---------:|
| Mixtral-8x7B Instruct 0.1  |          32768 |        0.1 |      8.7 |     0.04 | 
| Mixtral-8x22B Instruct 0.1 |          65536 |        0.1 |     14.5 |     1.21 |
| Llama 3 70B Instruct       |           8000 |        0.2 |      8.0 |     0.06 | 
| GPT-3.5-turbo              |          16384 |        0.0 |      5.0 |     0.06 | 
| GPT-4 Turbo                |         128000 |        3.9 |    45.17 |   222.62 | 
| GPT-4o                     |         128000 |        5.2 |    35.75 |   111.80 | 
| Claude 3 Opus              |         200000 |        5.4 |   338.43 |   502.28 | 
| Gemini 1.5 Pro             |        2000000 |        8.0 |       76 |      --- |
| LTMAgent 1 (Llama 3 70B)   |           8000 |        5.6 |   126.87 |     3.89 |
| LTMAgent 1 (GPT-4-turbo)   |          16384 |        5.3 |   326.22 |    87.78 |
| LTMAgent 1 (Claude)        |          16384 |        6.4 |   342.83 |   149.53 | 


### Benchmark 3 - 500k Memory Span

| Model                      | Context Tokens | Score / 11 | Time (m) | Cost ($) |
|----------------------------|---------------:|-----------:|---------:|---------:|
| Mixtral-8x7B Instruct 0.1  |          32768 |        0.1 |      8.5 |     0.07 | 
| Mixtral-8x22B Instruct 0.1 |          65536 |        0.1 |       44 |     1.15 |
| Llama 3 70B Instruct       |           8000 |        0.2 |     11.5 |     0.06 | 
| GPT-3.5-turbo              |          16384 |        0.0 |      6.5 |     0.06 | 
| GPT-4 Turbo                |         128000 |        1.0 |       48 |   223.16 | 
| GPT-4o                     |         128000 |        0.9 |       38 |   111.49 | 
| Claude 3 Opus              |         200000 |        3.4 |   324.35 |   527.86 | 
| Gemini 1.5 Pro             |        2000000 |        5.3 |     82.5 |      --- |
| LTMAgent 1 (Llama 3 70B)   |           8000 |        4.8 |   250.23 |     6.13 |
| LTMAgent 1 (GPT-4-turbo)   |          16384 |        3.1 |  1240.30 |   174.93 |
| LTMAgent 1 (Claude)        |          16384 |        4.9 |   528.37 |   230.27 | 

## Previous versions

- [Benchmark 1](https://github.com/GoodAI/goodai-ltm-benchmark/tree/v1-benchmark) (02/2024)
- [Benchmark 2](https://github.com/GoodAI/goodai-ltm-benchmark/tree/v2-benchmark) (03/2024)
- [Benchmark 3](https://github.com/GoodAI/goodai-ltm-benchmark/tree/v3-benchmark) (04/2024)

## Licence and usage
This project is licensed under the MIT License - see the LICENSE file for details. Use of this software requires attribution to the original author and project, as detailed in the license.

Some datasets use data generated by GPT, so those specific tests are unsuitable for commercial purposes.

If you have found this benchmark and these results useful, please cite our paper:
```
@inproceedings{
    castillo-bolado2024beyond,
    title={Beyond Prompts: Dynamic Conversational Benchmarking of Large Language Models},
    author={David Castillo-Bolado and Joseph Davidson and Finlay Gray and Marek Rosa},
    booktitle={The Thirty-eight Conference on Neural Information Processing Systems Datasets and Benchmarks Track},
    year={2024},
    url={https://openreview.net/forum?id=twFlD3C9Rt}
}
```

## Acknowledgements
* The filler is drawn from the [TriviaQA dataset](https://github.com/mandarjoshi90/triviaqa) which is licenced under Apache 2.0.
* The data for the SallyAnne dataset (labelled `data/tomi_data/`) was generated using [this code](https://github.com/kayburns/tom-qa-dataset) implementing the paper [Evaluating Theory of Mind in Question Answering](https://arxiv.org/abs/1808.09352), which is currently (as of 22/01/2024) unlicenced.
* The ChapterBreak dataset is described in the paper [ChapterBreak: A Challenge Dataset for Long-Range Language Models](https://arxiv.org/abs/2204.10878) and the repository is found on [GitHub](https://github.com/SimengSun/ChapterBreak). ChapterBreak is licenced under Apache 2.0.
* "The Complete Works of William Shakespeare" is public domain. This particular copy has been sourced from [Project Gutenburg](https://www.gutenberg.org/), whose terms of use can be found on their website.   
