# Quality

## Required Gate

```bash
./scripts/validate.sh
```

## Harness Expectations

- One command validates the repo.
- Docs describe only capabilities that exist or are clearly marked planned.
- Tests cover parser contracts before real incident traces are used.
- Raw private evidence is excluded from git.
- Reports are compact enough to hand to an agent without flooding context.
- Tool reports must distinguish nearby transcript context from proven tool-caused model calls.

## Phase 1 Acceptance

Toolburn is not Phase 1 complete until it can:

- parse selected OpenClaw/Codex local evidence sources
- attribute token usage by actor, tool-context, session, and time window
- preserve unknown attribution explicitly
- detect recurring and wait/poll-shaped burn paths
- export compact agent-readable drilldowns
- run offline without model calls or network access
