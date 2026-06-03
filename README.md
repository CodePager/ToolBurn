# Toolburn

Public CodePager module repo for building a local token burn profiler.

Toolburn starts as an offline CLI, roughly "`ncdu` for token burn." It reads
local evidence, normalizes actor/tool/session/token records, and reports the
burn paths that deserve optimization.

## Current Status

This repo contains the Phase 1 offline profiler spine. It can scan local
Codex/OpenClaw JSONL evidence into SQLite and report recent token burn by actor,
session, source, or tool. GitHub Copilot CLI session-state parsing is
experimental.

The active build plan is:

- [docs/exec-plans/active/toolburn-3-phase-plan.md](/srv/pager/repos/toolburn/docs/exec-plans/active/toolburn-3-phase-plan.md)

## Validate

```bash
./scripts/validate.sh
```

## CLI

Install or update the command:

```bash
curl -fsSL https://raw.githubusercontent.com/CodePager/toolburn/main/install.sh | sh
toolburn --help
```

From a checkout, install the local command:

```bash
cd /srv/pager/repos/toolburn
./scripts/install-local.sh
toolburn --help
```

Most humans and agents should start with:

```bash
toolburn recent --hours 23
```

See what Toolburn knows how to scan:

```bash
toolburn sources
```

Useful commands:

```bash
toolburn recent --hours 23 --limit 20
toolburn recent --hours 23 --no-scan
toolburn scan --db /tmp/toolburn.sqlite --openclaw /root/.openclaw/agents/main/agent/codex-home/sessions --codex /root/.codex/sessions --copilot /root/.copilot/session-state
toolburn top --db /tmp/toolburn.sqlite --by actor --since 2026-06-02T10:00:00.000Z
toolburn top --db /tmp/toolburn.sqlite --by tool --since 2026-06-02T10:00:00.000Z
toolburn explain --db /tmp/toolburn.sqlite <actor-or-session-id> --for-agent
toolburn export --db /tmp/toolburn.sqlite --target <actor-or-session-id>
```

Run `toolburn <command> --help` for command-specific options. From the repo
root, `./toolburn` also works without installation.

## Source Support

| Source | Status | Default path | Notes |
| --- | --- | --- | --- |
| Codex | Supported | `/root/.codex/sessions` | Reads `rollout-*.jsonl` token events. |
| OpenClaw | Supported | `/root/.openclaw/agents/main/agent/codex-home/sessions` | Reads OpenClaw-owned Codex transcripts and labels known background actors. |
| GitHub Copilot CLI | Experimental | `/root/.copilot/session-state` | Local Copilot installs keep session event logs at `~/.copilot/session-state/*/events.jsonl`. Toolburn reads `assistant.usage` rows when present and `session.shutdown.modelMetrics` cumulative usage when that is the only token evidence. |
| Claude Code | Untested | `~/.claude` | Claude Code support is not confirmed yet. Anthropic documents settings under `~/.claude/settings.json`, project settings under `.claude/settings.json`, and session-history controls such as `cleanupPeriodDays`, but Toolburn still needs a real Claude Code transcript sample before claiming support. |

Claude Code also uses `CLAUDE.md` instruction files, but those are context inputs,
not usage logs. Anthropic documents project/user locations such as `./CLAUDE.md`,
`./.claude/CLAUDE.md`, and `~/.claude/CLAUDE.md`.

References:

- [GitHub Copilot CLI README](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- [Claude Code settings](https://docs.anthropic.com/en/docs/claude-code/settings)
- [Claude Code memory](https://docs.anthropic.com/en/docs/claude-code/memory)
