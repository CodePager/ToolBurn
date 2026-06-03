# Toolburn

Token burn profiler for finding recurring model/tool usage paths and handing
agents compact optimization targets.

## Current Scope
- Offline CLI scaffold only.
- Phase 1 target: parse existing local evidence into SQLite and report burn by
  actor, tool, session, and time window.
- No model calls, no network, no daemon, no dashboard.

## Main Command
- `./scripts/validate.sh`

## Repo Rules
- Keep `AGENTS.md` short and map-like.
- Put execution truth in docs, tests, and source.
- Unknown attribution must remain explicitly unknown.

