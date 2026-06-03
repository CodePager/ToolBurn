# Toolburn

Private CodePager module repo for building a local token burn profiler.

Toolburn starts as an offline CLI, roughly "`ncdu` for token burn." It reads
local evidence, normalizes actor/tool/session/token records, and reports the
burn paths that deserve optimization.

## Current Status

This repo contains the harness scaffold and the first executable CLI skeleton.
The active build plan is:

- [docs/exec-plans/active/toolburn-3-phase-plan.md](/srv/pager/repos/toolburn/docs/exec-plans/active/toolburn-3-phase-plan.md)

## Validate

```bash
./scripts/validate.sh
```

## CLI

From the repo root:

```bash
python3 -m toolburn.cli --help
```

Set `PYTHONPATH=src` if running without an installed package.

