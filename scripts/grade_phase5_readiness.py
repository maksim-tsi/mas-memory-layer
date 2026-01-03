"""Phase 5 readiness summary emitter.

This script reads local readiness signals (coverage, environment availability)
and emits a concise JSON summary for grading. It does not read `.env`; it
relies on the caller's environment.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTMLCOV_STATUS = PROJECT_ROOT / "htmlcov" / "status.json"


def read_coverage() -> Optional[Dict[str, Any]]:
    """Return coverage summary if available."""
    if not HTMLCOV_STATUS.exists():
        return None
    try:
        return json.loads(HTMLCOV_STATUS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def env_flags() -> Dict[str, bool]:
    """Flag presence of key environment variables without reading secrets."""
    keys = [
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "MISTRAL_API_KEY",
        "DATA_NODE_IP",
    ]
    return {key: bool(os.environ.get(key)) for key in keys}


def build_summary() -> Dict[str, Any]:
    """Assemble readiness summary."""
    return {
        "coverage": read_coverage(),
        "env": env_flags(),
        "notes": {
            "coverage_source": str(HTMLCOV_STATUS.relative_to(PROJECT_ROOT)),
            "env_required_for_real_llm": "GOOGLE_API_KEY",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit Phase 5 readiness summary")
    parser.add_argument("--output", help="Optional path to write JSON summary", default=None)
    args = parser.parse_args()

    summary = build_summary()
    output_text = json.dumps(summary, indent=2, sort_keys=True)

    if args.output:
        out_path = Path(args.output).expanduser().resolve()
        out_path.write_text(output_text + "\n", encoding="utf-8")
        print(f"Summary written to {out_path}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()