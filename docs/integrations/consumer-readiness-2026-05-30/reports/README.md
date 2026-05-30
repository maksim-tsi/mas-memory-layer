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
| 2026-05-30 | `scm-skill-factory` | PASS with findings | `2026-05-30-scm-skill-factory-readiness-report.md` | n/a | Full synthetic readiness passed; expected Skill Factory domain-view/resource/prompt gaps are tracked in `../consumer-readiness-results-register.md`. |

Expected projects:

- `agentic-scm-tra26`
- `scm-skill-factory`
- `scm-cognitive-sandwich`

Reports must be sanitized. Do not include secrets, `.env` contents, provider API keys, passwords,
tokens, or private credentials.
