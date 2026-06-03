# Product Story

CodePager needs small, reliable modules before it becomes a broad control
plane. Toolburn is the first module because runaway token burn is both expensive
and operationally dangerous.

The product moment is simple:

```text
This recurring actor is burning tokens through this exact command. The cycles
are clean/no-op, the model is still being invoked, and this adapter shape will
remove the waste safely.
```

The user should not need a dashboard to understand the first answer. A terminal
report should be enough to decide what to fix.

## Non-Goals

- billing dashboard
- cloud telemetry product
- universal command wrapper
- model-based log analyst
- speculative attribution engine

## First Customer

The first customer is a human or agent investigating a local CodePager/OpenClaw
incident and trying to safely remove unnecessary model supervision from a
recurring background flow.

