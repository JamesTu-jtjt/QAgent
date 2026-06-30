# QAgent porting bundle

This folder supports reimplementing or embedding QAgent in another codebase.

| Document / artifact | Purpose |
|---------------------|---------|
| [../QAGENT_PORT_SPEC.md](../QAGENT_PORT_SPEC.md) | **Primary spec** — architecture, flows, APIs, schemas, security, integration guide |
| `prompts/*.yaml` | Verbatim prompt templates (copy from `qagent/backend/prompt_templates/`) |
| `prompts/team_notes/*.txt` | Per-team notes injected when a named QA team is selected |

**Source of truth:** The running implementation lives under `qagent/`. When this spec and code disagree, verify against code before integrating.

**Prompt sync:** After changing prompts in the app, refresh this bundle:

```bash
cp qagent/backend/prompt_templates/*.yaml docs/porting/prompts/
cp qagent/backend/prompt_templates/team_notes/*.txt docs/porting/prompts/team_notes/
```
