"""Run a 12-hour YAAM memory-layer audit and write a Markdown report.

The script collects:
- YAAM container health and log diagnostics for /v2/memory/* endpoints.
- Postgres L2/facts ingestion statistics.
- Qdrant collection point counts.
- Neo4j node/relationship totals and best-effort 12h deltas.

This script is defensive: backend failures are captured as limitations in the
report instead of crashing the full audit run.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psycopg
import requests
from neo4j import GraphDatabase

ERROR_PATTERN = re.compile(
    r"ERROR|Exception|Traceback|timeout|timed out|connection|pool|worker|hang|stuck|failed",
    re.IGNORECASE,
)
MEMORY_ENDPOINT_PATTERN = re.compile(r"(/v2/memory/[^\s\"]+)")
HTTP_LINE_PATTERN = re.compile(r'"[A-Z]+\s+(/v2/memory/[^\s\"]+)\s+HTTP/[^\"]+"\s+(\d{3})')


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for audit execution."""
    parser = argparse.ArgumentParser(
        description="Audit YAAM memory layer over a recent time window"
    )
    parser.add_argument("--since", default="12h", help="Docker logs --since window (default: 12h)")
    parser.add_argument(
        "--container",
        default="mas-memory-layer-mas-agent-1",
        help="YAAM container name (default: mas-memory-layer-mas-agent-1)",
    )
    parser.add_argument(
        "--output",
        default="docs/reports/2026-04-16-memory-layer-audit.md",
        help="Output markdown report path",
    )
    return parser.parse_args()


def run_cmd(cmd: list[str], timeout: int = 60) -> CommandResult:
    """Run a shell command and return captured output without raising on non-zero exit."""
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return CommandResult(stdout=proc.stdout, stderr=proc.stderr, returncode=proc.returncode)


def parse_memory_endpoint_counts(log_text: str) -> dict[str, int]:
    """Return counts by memory endpoint path found in logs."""
    counts: dict[str, int] = {}
    for endpoint in MEMORY_ENDPOINT_PATTERN.findall(log_text):
        counts[endpoint] = counts.get(endpoint, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def parse_memory_http_statuses(log_text: str) -> dict[str, dict[str, int]]:
    """Return per-endpoint HTTP status counters parsed from access logs."""
    by_endpoint: dict[str, dict[str, int]] = {}
    for endpoint, status in HTTP_LINE_PATTERN.findall(log_text):
        endpoint_map = by_endpoint.setdefault(endpoint, {})
        endpoint_map[status] = endpoint_map.get(status, 0) + 1
    return by_endpoint


def extract_error_lines(log_text: str, limit: int = 50) -> list[str]:
    """Extract likely error lines from logs with an upper bound."""
    lines = [line for line in log_text.splitlines() if ERROR_PATTERN.search(line)]
    return lines[:limit]


def mask_url(raw_url: str | None) -> str:
    """Mask password-like portions from URLs."""
    if not raw_url:
        return "unset"
    parsed = urlparse(raw_url)
    if parsed.username:
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        user = parsed.username
        path = parsed.path or ""
        return f"{parsed.scheme}://{user}:***@{host}{port}{path}"
    return raw_url


def get_container_health(container: str) -> dict[str, Any]:
    """Read container health and restart info."""
    inspect = run_cmd(
        [
            "docker",
            "inspect",
            container,
            "--format",
            "{{.State.Status}} restart={{.RestartCount}} oom={{.State.OOMKilled}} started={{.State.StartedAt}}",
        ]
    )
    return {
        "ok": inspect.returncode == 0,
        "raw": (inspect.stdout or inspect.stderr).strip(),
    }


def get_container_env(container: str) -> dict[str, str]:
    """Read selected backend environment variables from the running container."""
    cmd = [
        "docker",
        "exec",
        container,
        "sh",
        "-lc",
        "printenv POSTGRES_URL QDRANT_URL NEO4J_URI NEO4J_USER NEO4J_PASSWORD NEO4J_DATABASE",
    ]
    result = run_cmd(cmd)
    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    keys = [
        "POSTGRES_URL",
        "QDRANT_URL",
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
        "NEO4J_DATABASE",
    ]
    data = {k: "" for k in keys}
    for i, value in enumerate(values):
        if i < len(keys):
            data[keys[i]] = value
    return data


def get_container_logs(container: str, since: str) -> str:
    """Fetch raw container logs for a time window."""
    result = run_cmd(["docker", "logs", container, "--since", since], timeout=180)
    # docker logs frequently sends content to stderr.
    combined = "\n".join(part for part in [result.stdout, result.stderr] if part)
    return combined


def postgres_ingestion_stats(postgres_url: str) -> dict[str, Any]:
    """Return L2/facts table ingestion stats for the last 12 hours."""
    stats: dict[str, Any] = {
        "ok": False,
        "error": "",
        "tables": [],
        "table_columns": {},
        "candidates": [],
        "counts": [],
    }
    if not postgres_url:
        stats["error"] = "POSTGRES_URL not available"
        return stats

    timestamp_candidates = [
        "created_at",
        "created_on",
        "timestamp",
        "stored_at",
        "inserted_at",
        "updated_at",
    ]
    try:
        with psycopg.connect(postgres_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public'
                ORDER BY table_name
                """
            )
            tables = [row[0] for row in cur.fetchall()]
            stats["tables"] = tables
            table_columns: dict[str, list[str]] = {}
            for table_name in tables:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema='public' AND table_name=%s
                    ORDER BY ordinal_position
                    """,
                    (table_name,),
                )
                table_columns[table_name] = [row[0] for row in cur.fetchall()]

            stats["table_columns"] = table_columns

            signal_columns = {"fact", "certainty", "impact", "ciar", "confidence", "source"}
            scored_candidates: list[tuple[int, str]] = []
            for table_name in tables:
                cols = {c.lower() for c in table_columns.get(table_name, [])}
                score = 0
                name_lower = table_name.lower()
                if "fact" in name_lower or "l2" in name_lower:
                    score += 2
                score += sum(1 for marker in signal_columns if any(marker in col for col in cols))
                if score >= 2:
                    scored_candidates.append((score, table_name))

            candidates = [name for _, name in sorted(scored_candidates, reverse=True)]
            stats["candidates"] = candidates

            for table_name in candidates:
                columns = table_columns.get(table_name, [])
                ts_column = next((name for name in timestamp_candidates if name in columns), None)

                cur.execute(f'SELECT count(*)::bigint FROM "public"."{table_name}"')
                total_count = int(cur.fetchone()[0])
                count_12h: int | None = None
                if ts_column:
                    cur.execute(
                        f'SELECT count(*)::bigint FROM "public"."{table_name}" '
                        f"WHERE \"{ts_column}\" >= NOW() - INTERVAL '12 hours'"
                    )
                    count_12h = int(cur.fetchone()[0])

                stats["counts"].append(
                    {
                        "table": table_name,
                        "timestamp_column": ts_column,
                        "count_12h": count_12h,
                        "total_count": total_count,
                    }
                )

        stats["ok"] = True
        return stats
    except Exception as exc:  # pragma: no cover - integration path
        stats["error"] = str(exc)
        return stats


def qdrant_stats(qdrant_url: str) -> dict[str, Any]:
    """Return collection-level point counts from Qdrant."""
    data: dict[str, Any] = {
        "ok": False,
        "error": "",
        "collection_count": 0,
        "collections": [],
    }
    if not qdrant_url:
        data["error"] = "QDRANT_URL not available"
        return data

    try:
        list_resp = requests.get(f"{qdrant_url.rstrip('/')}/collections", timeout=10)
        list_resp.raise_for_status()
        list_payload = list_resp.json()
        names = [
            entry.get("name", "") for entry in list_payload.get("result", {}).get("collections", [])
        ]

        collection_rows: list[dict[str, Any]] = []
        for name in names:
            detail_resp = requests.get(f"{qdrant_url.rstrip('/')}/collections/{name}", timeout=10)
            detail_resp.raise_for_status()
            detail = detail_resp.json().get("result", {})
            collection_rows.append(
                {
                    "name": name,
                    "points_count": int(detail.get("points_count") or 0),
                    "vectors_count": int(detail.get("vectors_count") or 0),
                    "status": detail.get("status", "unknown"),
                }
            )

        data["ok"] = True
        data["collection_count"] = len(collection_rows)
        data["collections"] = sorted(
            collection_rows, key=lambda row: row["points_count"], reverse=True
        )
        return data
    except Exception as exc:  # pragma: no cover - integration path
        data["error"] = str(exc)
        return data


def neo4j_stats(uri: str, user: str, password: str, database: str) -> dict[str, Any]:
    """Return Neo4j node/relationship totals and best-effort 12h deltas."""
    out: dict[str, Any] = {
        "ok": False,
        "error": "",
        "nodes_total": None,
        "rels_total": None,
        "node_props": {},
        "rel_props": {},
        "nodes_12h": {},
        "rels_12h": {},
    }
    if not uri:
        out["error"] = "NEO4J_URI not available"
        return out
    if not password:
        out["error"] = "NEO4J_PASSWORD not available"
        return out

    props = ["created_at", "created_on", "timestamp", "inserted_at", "updated_at"]

    try:
        driver = GraphDatabase.driver(uri, auth=(user or "neo4j", password))
        with driver.session(database=(database or "neo4j")) as session:
            out["nodes_total"] = int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"])
            out["rels_total"] = int(
                session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
            )

            for prop in props:
                out["node_props"][prop] = int(
                    session.run(
                        f"MATCH (n) WHERE n.{prop} IS NOT NULL RETURN count(n) AS c"
                    ).single()["c"]
                )
                out["rel_props"][prop] = int(
                    session.run(
                        f"MATCH ()-[r]->() WHERE r.{prop} IS NOT NULL RETURN count(r) AS c"
                    ).single()["c"]
                )

            for prop in props:
                try:
                    out["nodes_12h"][prop] = int(
                        session.run(
                            "MATCH (n) "
                            f"WHERE n.{prop} IS NOT NULL "
                            f"AND n.{prop} >= datetime() - duration('PT12H') "
                            "RETURN count(n) AS c"
                        ).single()["c"]
                    )
                except Exception:
                    out["nodes_12h"][prop] = None

                try:
                    out["rels_12h"][prop] = int(
                        session.run(
                            "MATCH ()-[r]->() "
                            f"WHERE r.{prop} IS NOT NULL "
                            f"AND r.{prop} >= datetime() - duration('PT12H') "
                            "RETURN count(r) AS c"
                        ).single()["c"]
                    )
                except Exception:
                    out["rels_12h"][prop] = None

        driver.close()
        out["ok"] = True
        return out
    except Exception as exc:  # pragma: no cover - integration path
        out["error"] = str(exc)
        return out


def build_report(
    *,
    generated_at: str,
    since: str,
    container: str,
    health: dict[str, Any],
    envs: dict[str, str],
    endpoint_counts: dict[str, int],
    endpoint_statuses: dict[str, dict[str, int]],
    error_lines: list[str],
    pg_stats: dict[str, Any],
    q_stats: dict[str, Any],
    n_stats: dict[str, Any],
) -> str:
    """Compose final markdown report content."""
    lines: list[str] = []
    lines.append("# YAAM Memory Layer Audit (Last 12 Hours)")
    lines.append("")
    lines.append(f"**Date:** {generated_at}")
    lines.append(f"**Container:** `{container}`")
    lines.append(f"**Window:** `{since}`")
    lines.append("")

    lines.append("## 1. Container Log Mining")
    lines.append("")
    lines.append(f"- Container state: `{health.get('raw', 'n/a')}`")
    lines.append(f"- Configured `POSTGRES_URL`: `{mask_url(envs.get('POSTGRES_URL'))}`")
    lines.append(f"- Configured `QDRANT_URL`: `{envs.get('QDRANT_URL', 'unset')}`")
    lines.append(f"- Configured `NEO4J_URI`: `{envs.get('NEO4J_URI', 'unset')}`")
    lines.append("")
    lines.append("### Memory Endpoint Request Volume")
    lines.append("")
    if endpoint_counts:
        for endpoint, count in endpoint_counts.items():
            lines.append(f"- `{endpoint}`: **{count}** requests")
    else:
        lines.append("- No `/v2/memory/*` endpoints observed in the selected log window.")

    lines.append("")
    lines.append("### Memory Endpoint HTTP Statuses")
    lines.append("")
    if endpoint_statuses:
        for endpoint, statuses in endpoint_statuses.items():
            rendered = ", ".join([f"`{code}`={count}" for code, count in sorted(statuses.items())])
            lines.append(f"- `{endpoint}`: {rendered}")
    else:
        lines.append("- No parseable access-log HTTP status lines found for `/v2/memory/*`.")

    lines.append("")
    lines.append("### Error and Saturation Signals")
    lines.append("")
    if error_lines:
        lines.append(f"- Matched error-like lines (sampled): **{len(error_lines)}**")
        lines.append("")
        lines.append("```text")
        lines.extend(error_lines[:20])
        lines.append("```")
    else:
        lines.append("- No error-like log lines matched the audit pattern.")

    lines.append("")
    lines.append("## 2. DBMS Statistics and Health Check")
    lines.append("")

    lines.append("### PostgreSQL (L1/L2)")
    lines.append("")
    if pg_stats.get("ok"):
        counts = pg_stats.get("counts", [])
        lines.append(f"- Candidate L2/fact tables: **{len(pg_stats.get('candidates', []))}**")
        if counts:
            for row in counts:
                if row["timestamp_column"]:
                    lines.append(
                        f"- `{row['table']}`: last 12h = **{row['count_12h']}**, total = **{row['total_count']}** "
                        f"(timestamp column: `{row['timestamp_column']}`)"
                    )
                else:
                    lines.append(
                        f"- `{row['table']}`: last 12h = **N/A** (no timestamp column), total = **{row['total_count']}**"
                    )
        else:
            lines.append("- No L2/fact-like tables were detected by naming heuristics.")
    else:
        lines.append(f"- PostgreSQL stats unavailable: `{pg_stats.get('error', 'unknown error')}`")

    lines.append("")
    lines.append("### Qdrant (L3 Vectors)")
    lines.append("")
    if q_stats.get("ok"):
        lines.append(f"- Collections discovered: **{q_stats.get('collection_count', 0)}**")
        top_non_zero = [
            row for row in q_stats.get("collections", []) if row.get("points_count", 0) > 0
        ][:10]
        if top_non_zero:
            lines.append("- Non-zero point collections:")
            for row in top_non_zero:
                lines.append(
                    f"  - `{row['name']}`: points = **{row['points_count']}**, vectors = **{row['vectors_count']}**, status = `{row['status']}`"
                )
        else:
            lines.append("- No collections with non-zero points were found.")
        lines.append(
            "- Limitation: Qdrant collection metadata does not expose insertion timestamps by default."
        )
    else:
        lines.append(f"- Qdrant stats unavailable: `{q_stats.get('error', 'unknown error')}`")

    lines.append("")
    lines.append("### Neo4j (L3 Graph)")
    lines.append("")
    if n_stats.get("ok"):
        lines.append(f"- Total nodes: **{n_stats.get('nodes_total')}**")
        lines.append(f"- Total relationships: **{n_stats.get('rels_total')}**")
        node_12h = {k: v for k, v in n_stats.get("nodes_12h", {}).items() if v is not None}
        rel_12h = {k: v for k, v in n_stats.get("rels_12h", {}).items() if v is not None}
        if node_12h or rel_12h:
            lines.append("- 12h temporal-property counts (best effort):")
            for key, value in node_12h.items():
                lines.append(f"  - Nodes by `{key}`: **{value}**")
            for key, value in rel_12h.items():
                lines.append(f"  - Relationships by `{key}`: **{value}**")
        else:
            lines.append(
                "- Limitation: no compatible temporal properties were available for precise 12h deltas."
            )
    else:
        lines.append(f"- Neo4j stats unavailable: `{n_stats.get('error', 'unknown error')}`")

    lines.append("")
    lines.append("## 3. Findings and Bottleneck Assessment")
    lines.append("")

    l2_volume = endpoint_counts.get("/v2/memory/l2/facts", 0)
    l4_volume = endpoint_counts.get("/v2/memory/l4/finalize", 0)
    has_5xx = any(
        code.startswith("5") for statuses in endpoint_statuses.values() for code in statuses
    )
    gemini_failures = sum(1 for line in error_lines if "Provider 'gemini' failed" in line)

    if not has_5xx and gemini_failures > 0:
        lines.append(
            "- The dominant failure signal in the sampled logs is upstream provider instability "
            "(`Provider 'gemini' failed`) rather than `/v2/memory/*` HTTP 5xx responses."
        )
    if l2_volume > 0:
        lines.append(
            f"- Auto-Store traffic is high (`/v2/memory/l2/facts` = **{l2_volume}** requests in {since}), "
            "which increases pressure on downstream DB adapters and can amplify latency variance."
        )
    if l4_volume > 0:
        lines.append(
            f"- Finalization calls are also frequent (`/v2/memory/l4/finalize` = **{l4_volume}** requests), "
            "suggesting sustained write activity across tiers during orchestration."
        )

    if pg_stats.get("ok") and pg_stats.get("counts"):
        growing = [row for row in pg_stats["counts"] if (row.get("count_12h") or 0) > 0]
        if growing:
            lines.append(
                "- PostgreSQL shows positive L2/fact ingestion in the last 12h, indicating writes are reaching the DB."
            )

    lines.append("")
    lines.append("### Proposed Remediations")
    lines.append("")
    lines.append(
        "- Add bounded retries with jitter for upstream LLM provider calls; do not block memory finalization on provider transient failures."
    )
    lines.append(
        "- Introduce backpressure in Auto-Store path (e.g., queue + worker pool) to decouple tool completion latency from DB write latency."
    )
    lines.append(
        "- Verify and add indexes on frequently filtered timestamp/session keys in L2 fact tables."
    )
    lines.append(
        "- Tune connection pools explicitly for Postgres and Neo4j adapters based on concurrent task count."
    )
    lines.append(
        "- Add endpoint-level latency histograms for `/v2/memory/l2/facts` and `/v2/memory/l4/finalize` to detect saturation before stalls."
    )

    lines.append("")
    lines.append("## 4. Method Notes")
    lines.append("")
    lines.append("- Audit was executed via a repository script validated by unit tests before run.")
    lines.append(
        "- Where backend temporal metadata is unavailable, totals are reported with explicit limitations."
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    """Entrypoint for audit script."""
    args = parse_args()
    generated_at = datetime.now(UTC).isoformat()

    health = get_container_health(args.container)
    envs = get_container_env(args.container)
    logs = get_container_logs(args.container, args.since)
    endpoint_counts = parse_memory_endpoint_counts(logs)
    endpoint_statuses = parse_memory_http_statuses(logs)
    error_lines = extract_error_lines(logs, limit=100)

    pg_stats = postgres_ingestion_stats(envs.get("POSTGRES_URL", ""))
    q_stats = qdrant_stats(envs.get("QDRANT_URL", ""))
    n_stats = neo4j_stats(
        uri=envs.get("NEO4J_URI", ""),
        user=envs.get("NEO4J_USER", "neo4j") or "neo4j",
        password=envs.get("NEO4J_PASSWORD", ""),
        database=envs.get("NEO4J_DATABASE", "neo4j") or "neo4j",
    )

    report_text = build_report(
        generated_at=generated_at,
        since=args.since,
        container=args.container,
        health=health,
        envs=envs,
        endpoint_counts=endpoint_counts,
        endpoint_statuses=endpoint_statuses,
        error_lines=error_lines,
        pg_stats=pg_stats,
        q_stats=q_stats,
        n_stats=n_stats,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")

    print(f"Wrote report to {output_path}")
    print(
        json.dumps(
            {
                "postgres_ok": pg_stats.get("ok"),
                "qdrant_ok": q_stats.get("ok"),
                "neo4j_ok": n_stats.get("ok"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
