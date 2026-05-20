"""Aggregate CIAR policy experiment artifacts across run directories."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REQUIRED_ARTIFACTS = (
    "summary.md",
    "promotion_results.json",
    "alternative_scores.json",
    "events.jsonl",
    "run_manifest.json",
)


@dataclass
class ScenarioAggregate:
    runs: int = 0
    segments_promoted: int = 0
    facts_extracted: int = 0
    facts_promoted: int = 0
    facts_filtered: int = 0
    facts_review_only: int = 0
    facts_suppressed: int = 0
    errors: int = 0
    raw_stored_delta_sum: float = 0.0
    raw_stored_delta_count: int = 0
    promoted_contents: list[str] = field(default_factory=list)
    review_only_contents: list[str] = field(default_factory=list)
    suppressed_contents: list[str] = field(default_factory=list)

    def add_promotion_stats(self, stats: dict[str, Any]) -> None:
        self.runs += 1
        self.segments_promoted += int(stats.get("segments_promoted", 0) or 0)
        self.facts_extracted += int(stats.get("facts_extracted", 0) or 0)
        self.facts_promoted += int(stats.get("facts_promoted", 0) or 0)
        self.facts_filtered += int(stats.get("facts_filtered", 0) or 0)
        self.facts_review_only += int(stats.get("facts_review_only", 0) or 0)
        self.facts_suppressed += int(stats.get("facts_suppressed", 0) or 0)
        self.errors += int(stats.get("errors", 0) or 0)

    def add_score_delta(self, raw: Any, stored: Any) -> None:
        if not isinstance(raw, int | float) or not isinstance(stored, int | float):
            return
        self.raw_stored_delta_sum += float(stored) - float(raw)
        self.raw_stored_delta_count += 1

    def to_dict(self) -> dict[str, Any]:
        avg_delta = None
        if self.raw_stored_delta_count:
            avg_delta = self.raw_stored_delta_sum / self.raw_stored_delta_count
        return {
            "runs": self.runs,
            "segments_promoted": self.segments_promoted,
            "facts_extracted": self.facts_extracted,
            "facts_promoted": self.facts_promoted,
            "facts_filtered": self.facts_filtered,
            "facts_review_only": self.facts_review_only,
            "facts_suppressed": self.facts_suppressed,
            "errors": self.errors,
            "avg_stored_minus_raw_ciar": avg_delta,
            "promoted_contents": self.promoted_contents,
            "review_only_contents": self.review_only_contents,
            "suppressed_contents": self.suppressed_contents,
        }


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def infer_contradiction_policy(run_id: str, manifest: dict[str, Any]) -> str:
    runtime = manifest.get("runtime") or {}
    if runtime.get("contradiction_policy_mode"):
        return str(runtime["contradiction_policy_mode"])
    lower_run_id = run_id.lower()
    if "suppress" in lower_run_id or "supersession" in lower_run_id:
        return "suppress_superseded"
    if "metadata" in lower_run_id:
        return "metadata_only"
    return "off"


def infer_promotion_policy(
    manifest: dict[str, Any],
    promotion_results: dict[str, Any],
) -> str:
    runtime = manifest.get("runtime") or {}
    if runtime.get("promotion_policy_mode"):
        return str(runtime["promotion_policy_mode"])
    for stats in promotion_results.values():
        if isinstance(stats, dict) and stats.get("promotion_policy_mode"):
            return str(stats["promotion_policy_mode"])
    return "unknown"


def scenario_from_session_id(session_id: str) -> str | None:
    if "__" not in session_id:
        return None
    return session_id.rsplit("__", 1)[-1]


def analyze_run(run_dir: Path) -> dict[str, Any]:
    manifest = read_json(run_dir / "run_manifest.json", {})
    promotion_results = read_json(run_dir / "promotion_results.json", {})
    alternative_scores = read_json(run_dir / "alternative_scores.json", [])
    events = read_jsonl(run_dir / "events.jsonl")
    run_id = str(manifest.get("run_id") or run_dir.name)
    promotion_policy = infer_promotion_policy(manifest, promotion_results)
    contradiction_policy = infer_contradiction_policy(run_id, manifest)

    artifacts = {name: (run_dir / name).exists() for name in REQUIRED_ARTIFACTS}
    scenarios: dict[str, ScenarioAggregate] = defaultdict(ScenarioAggregate)

    for scenario_id, stats in promotion_results.items():
        if isinstance(stats, dict):
            scenarios[str(scenario_id)].add_promotion_stats(stats)

    for row in alternative_scores:
        if not isinstance(row, dict):
            continue
        scenario_id = row.get("scenario_id")
        if not scenario_id:
            continue
        aggregate = scenarios[str(scenario_id)]
        aggregate.add_score_delta(row.get("raw_fact_ciar"), row.get("stored_ciar"))
        content = str(row.get("content") or "")
        if row.get("suppressed"):
            aggregate.suppressed_contents.append(content)
        elif row.get("review_only"):
            aggregate.review_only_contents.append(content)
        else:
            aggregate.promoted_contents.append(content)

    for event in events:
        event_type = event.get("event_type")
        if event_type not in {"fact_review_only", "fact_suppressed"}:
            continue
        scenario_id = scenario_from_session_id(str(event.get("session_id") or ""))
        if not scenario_id:
            continue
        content = str((event.get("data") or {}).get("content") or "")
        if not content:
            continue
        if event_type == "fact_review_only":
            scenarios[scenario_id].review_only_contents.append(content)
        elif event_type == "fact_suppressed":
            scenarios[scenario_id].suppressed_contents.append(content)

    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "completed": bool(manifest.get("completed_at")),
        "dry_run": bool(manifest.get("dry_run", False)),
        "model": manifest.get("model"),
        "promotion_policy_mode": promotion_policy,
        "contradiction_policy_mode": contradiction_policy,
        "phoenix_project_name": manifest.get("phoenix_project_name"),
        "provider_health": manifest.get("provider_health"),
        "cleanup": manifest.get("cleanup"),
        "artifacts": artifacts,
        "scenarios": {key: value.to_dict() for key, value in sorted(scenarios.items())},
    }


def aggregate_runs(run_dirs: list[Path]) -> dict[str, Any]:
    runs = [analyze_run(path) for path in run_dirs]
    by_config: dict[str, dict[str, ScenarioAggregate]] = defaultdict(
        lambda: defaultdict(ScenarioAggregate)
    )
    artifact_gaps: list[dict[str, Any]] = []

    for run in runs:
        config_key = (
            f"{run['promotion_policy_mode']}+{run['contradiction_policy_mode']}"
        )
        missing = [name for name, present in run["artifacts"].items() if not present]
        if missing:
            artifact_gaps.append({"run_id": run["run_id"], "missing": missing})
        for scenario_id, stats in run["scenarios"].items():
            aggregate = by_config[config_key][scenario_id]
            aggregate.runs += int(stats["runs"])
            aggregate.segments_promoted += int(stats["segments_promoted"])
            aggregate.facts_extracted += int(stats["facts_extracted"])
            aggregate.facts_promoted += int(stats["facts_promoted"])
            aggregate.facts_filtered += int(stats["facts_filtered"])
            aggregate.facts_review_only += int(stats["facts_review_only"])
            aggregate.facts_suppressed += int(stats["facts_suppressed"])
            aggregate.errors += int(stats["errors"])
            if stats["avg_stored_minus_raw_ciar"] is not None:
                count = len(stats["promoted_contents"])
                aggregate.raw_stored_delta_sum += (
                    float(stats["avg_stored_minus_raw_ciar"]) * count
                )
                aggregate.raw_stored_delta_count += count
            aggregate.promoted_contents.extend(stats["promoted_contents"])
            aggregate.review_only_contents.extend(stats["review_only_contents"])
            aggregate.suppressed_contents.extend(stats["suppressed_contents"])

    summary = {
        config_key: {
            scenario_id: scenario.to_dict()
            for scenario_id, scenario in sorted(scenarios.items())
        }
        for config_key, scenarios in sorted(by_config.items())
    }
    return {
        "run_count": len(runs),
        "runs": runs,
        "artifact_gaps": artifact_gaps,
        "by_config": summary,
        "recommendation_inputs": build_recommendation_inputs(summary),
    }


def build_recommendation_inputs(by_config: dict[str, Any]) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for config_key, scenarios in by_config.items():
        small_talk = scenarios.get("small_talk", {})
        segment_mismatch = scenarios.get("segment_mismatch", {})
        contradiction = scenarios.get("contradiction_update", {})
        inputs[config_key] = {
            "small_talk_promoted": small_talk.get("facts_promoted", 0),
            "segment_mismatch_promoted": segment_mismatch.get("facts_promoted", 0),
            "segment_mismatch_review_only": segment_mismatch.get(
                "facts_review_only", 0
            ),
            "contradiction_promoted": contradiction.get("facts_promoted", 0),
            "contradiction_review_only": contradiction.get("facts_review_only", 0),
            "contradiction_suppressed": contradiction.get("facts_suppressed", 0),
            "errors": sum(
                int(stats.get("errors", 0) or 0) for stats in scenarios.values()
            ),
        }
    return inputs


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CIAR Default Policy Analysis",
        "",
        f"- runs_analyzed: `{report['run_count']}`",
        "",
        "## Recommendation Inputs",
        "",
        (
            "| Config | Small Talk Promoted | Segment Mismatch Promoted | "
            "Segment Mismatch Review-Only | Contradiction Promoted | "
            "Contradiction Review-Only | Contradiction Suppressed | Errors |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for config_key, stats in sorted(report["recommendation_inputs"].items()):
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{config_key}`",
                    str(stats["small_talk_promoted"]),
                    str(stats["segment_mismatch_promoted"]),
                    str(stats["segment_mismatch_review_only"]),
                    str(stats["contradiction_promoted"]),
                    str(stats["contradiction_review_only"]),
                    str(stats["contradiction_suppressed"]),
                    str(stats["errors"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Artifact Gaps", ""])
    if report["artifact_gaps"]:
        for gap in report["artifact_gaps"]:
            lines.append(f"- `{gap['run_id']}` missing: {', '.join(gap['missing'])}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate CIAR default-policy experiment artifacts."
    )
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = aggregate_runs(args.run_dirs)
    rendered_json = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output:
        args.json_output.write_text(rendered_json + "\n", encoding="utf-8")
    else:
        print(rendered_json)
    if args.markdown_output:
        args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
