# Consumer Readiness Reports

Store 2026-05-30 consumer readiness reports here.

Use the template at `../readiness-report-template.md`.

Recommended naming convention:

```text
YYYY-MM-DD-<project-id>-readiness-report.md
```

External consumer reports may preserve their original timestamped filenames when copied as immutable
evidence.

## Received Reports

| Received | Project | Verdict | Report | Structured results | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-05-30 | `agentic-scm-tra26` | PASS | `20260530T153445Z-agentic-scm-tra26-full-synthetic-report.md` | `20260530T153445Z-agentic-scm-tra26-full-synthetic-results.json` | Full synthetic readiness passed; see `../consumer-readiness-results-register.md` for triage and coverage evaluation. |
| 2026-05-30 | `scm-skill-factory` | PASS with findings | `2026-05-30-scm-skill-factory-readiness-report.md` | n/a | Initial synthetic readiness passed with Skill Factory domain-view/resource/prompt gaps; resolved by the 2026-05-31 retest below. |
| 2026-05-31 | `scm-skill-factory` | PASS | `2026-05-31-scm-skill-factory-readiness-report.md` | n/a | Post-fix write-enabled retest passed; all Skill Factory domain-pack views, including run episodes, returned records. |

Expected projects:

- `agentic-scm-tra26`
- `scm-skill-factory`
- `scm-cognitive-sandwich`

Reports must be sanitized. Do not include secrets, `.env` contents, provider API keys, passwords,
tokens, or private credentials.
