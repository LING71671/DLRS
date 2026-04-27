# `runtime/` — DLRS reference runtime

Reference implementation of the `life-runtime v0.1.1` protocol defined in
[`docs/LIFE_RUNTIME_STANDARD.md`](../docs/LIFE_RUNTIME_STANDARD.md).

Tracking epic: [#119](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/119)
(v0.9 — Reference Runtime Implementation).

## Layout

```
runtime/
├── __init__.py              exports __version__ + Runtime stub
├── cli/lifectl.py           lifectl CLI entrypoint
├── verify/                  Stage 1 — sub-issue #121
├── resolve/                 Stage 2 — sub-issue #122
├── assemble/                Stage 3 — sub-issue #123
├── run/                     Stage 4 — sub-issue #124
├── guard/                   Stage 5 — sub-issue #125
├── providers/               built-in echo Provider — sub-issue #126
└── audit/                   runtime-side hash-chain emitter — sub-issue #125
```

## Quickstart (post-v0.9)

```
pip install -e .                      # from repo root
lifectl version                       # confirm install
lifectl info  examples/minimal-life-package/out/*.life --withdrawal-mock not-revoked
lifectl run   examples/minimal-life-package/out/*.life --withdrawal-mock not-revoked
```

As of v0.9 sub-issue #121, Stage 1 Verify is wired:

- `lifectl info <pkg>` prints a structured §2.1–§2.5 + lifecycle report
  (human-readable by default, JSON via `--json`) and exits **0** on PASS /
  **1** on FAIL.
- `lifectl run <pkg>` runs Stage 1 then exits **2** with a "Stage 2+ pending
  sub-issues #122-#126" message; full mount comes online sub-issue by
  sub-issue.

`--withdrawal-mock` is **test-only**; production runtimes MUST omit it so
the §2.5 withdrawal endpoint is genuinely polled over HTTP.

## Why a separate Python package?

The repo's existing `tools/` directory hosts authoring + validation tooling
(builders, schema linters, pipeline drivers). The runtime is a different
artifact: it loads a finished `.life`, not authors one. Separating the two
keeps the dependency graph clean — `tools/` continues to work with
`tools/requirements.txt`, while `runtime/` is installable via
`pyproject.toml` (`pip install -e .`).

## Spec conformance

`life-runtime v0.1.1` includes everything from v0.1 (load sequence, mount
semantics, runtime obligations, termination) plus v0.8 Part B 5-stage
assembly + Provider Registry + graded sandbox + hosted-API AND-gate.
The `runtime/` package implements **the full v0.1.1 spec** for **single
`.life`** sessions only — multi-`.life` ensemble + `.world` + plugins are
v0.10+ work.
