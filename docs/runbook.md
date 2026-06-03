# Runbook

## Local Validation

Run the full scaffold check:

```bash
./scripts/validate.sh
```

The validator checks required docs, Python syntax, unit tests, CLI help, schema
creation, generated-file hygiene, and obvious secret-shaped strings.

## Local CLI

```bash
PYTHONPATH=src python3 -m toolburn.cli --help
PYTHONPATH=src python3 -m toolburn.cli schema --db /tmp/toolburn.sqlite
```

## Evidence Handling

- Keep raw session logs, private incident traces, and personal-agent transcripts
  outside git.
- Store only fixtures that are synthetic or explicitly sanitized.
- Prefer compact JSON summaries with counts, hashes, timestamps, and sample
  bounds instead of raw log bodies.

## Phase 1 Closeout Proof

Before moving a Phase 1 plan to completed, capture:

- validation command and output
- exact parser sources supported
- sample `du`, `top`, `tree`, and `explain --for-agent` outputs
- evidence that the run used no model calls and no network

