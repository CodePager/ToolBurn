# Adapter Contract

Adapters are planned for Phase 3. The contract is documented now so Phase 1
reports collect the fields adapters will need later.

## Goal

An adapter turns noisy tool output into a deterministic, compact escalation
payload. Clean/no-op cycles should avoid model invocation when policy allows it.

## Planned Shape

```text
adapters/<name>/
  adapter.yml
  summarize.py
  verify.py
  fixtures/
    clean-output.json
    candidate-output.json
    error-output.json
  README.md
```

## Required Semantics

- declare the input command
- declare safe no-op conditions
- emit candidate and error counts
- emit bounded examples
- emit stable output hashes
- define verification steps
- define rollback steps

## Safety Rule

No adapter may hide candidates or errors to save tokens. Token savings come from
compact deterministic representation, not from dropping meaningful work.

