# Lessons Learned Register

This register captures recurring issues surfaced during development and the mitigations that resolve them. Entries should be concise, structured, and updated immediately after an incident is resolved.

## Usage Guidelines
- Document only project-specific incidents that produced unexpected failures or workflow friction.
- Prefer objective wording; avoid speculation unless clearly marked as a hypothesis.
- Include enough context (environment, command, files) so another engineer can reproduce or validate the scenario.
- Link to supporting artifacts such as logs, pull requests, or chat transcripts when available.

## Entry Template
Use the following table format for all new entries. Update the `Status` column as mitigations are adopted or superseded.

| Date       | Incident ID           | Environment        | Symptom                                                                 | Root Cause                                                                                   | Mitigation                                                                                                    | Status   | References |
|------------|-----------------------|--------------------|-------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|----------|------------|
| YYYY-MM-DD | LL-YYYYMMDD-XX        | Host + OS details | Brief error description (command/test/etc.)                             | Concise explanation of why the issue occurred                                                | Specific steps, scripts, or instruction updates that prevent recurrence                                      | Active   | Links      |

## Entries

| Date       | Incident ID            | Environment                        | Symptom                                                                                               | Root Cause                                                                                                    | Mitigation                                                                                                                                                   | Status   | References |
|------------|------------------------|------------------------------------|-------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|------------|
| 2025-11-15 | LL-20251115-01         | Local macOS checkout (`dev` branch) | `run_in_terminal` reported "no output" after commands with `> /tmp/... && cat /tmp/...` chaining. | Main command exited non-zero (missing binary), so the `&& cat` step never executed, hiding captured stderr. | Always capture output to `/tmp/*.out` but follow with `; cat /tmp/*.out` (or separate `cat` command) so logs surface even when the primary command fails. Update instructions to note this pattern. | Adopted  | Session log 2025-11-15 |
