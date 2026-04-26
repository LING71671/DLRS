# DLRS v0.5 Pipeline Guide

> Companion to `examples/asr-demo/README.md`. The demo answers *"can I run it?"*; this guide answers *"how is it built and what guarantees can I rely on?"*.

DLRS v0.5 introduces four offline-first build pipelines that turn raw artefacts referenced by a record into derived assets fit for downstream consumption (registry display, RAG, moderation review). All four pipelines share the same contract, the same provenance descriptor, and the same hard offline-first invariant — they exist primarily to keep the rest of DLRS honest about *where* its derived data comes from.

## 0. Mental model

```
record/
├── manifest.json
├── public_profile.json
├── artifacts/raw_pointers/audio/voice.pointer.json   # or repo://artifacts/raw/audio/voice.wav
└── derived/
    ├── asr/voice.transcript.json              # pipeline: asr
    ├── asr/voice.transcript.descriptor.json
    ├── text/voice.clean.txt                   # pipeline: text
    ├── text/voice.redactions.json
    ├── text/voice.clean.descriptor.json
    ├── vectorization/voice.index.json         # pipeline: vectorization
    ├── vectorization/voice.index.descriptor.json
    ├── moderation/voice.moderation.json       # pipeline: moderation
    └── moderation/voice.moderation.descriptor.json
```

The full chain is `audio → asr → text → {vectorization, moderation}`. Each step writes its output under `derived/<pipeline-name>/` and a sibling `<stem>.descriptor.json` provenance file that **always** validates against `schemas/derived-asset.schema.json`.

You do not have to run all four. Each pipeline accepts an explicit `--input` so the chain can be entered at any stage.

## 1. The pipeline contract (issue #30 / #35)

Every pipeline is registered in `pipelines/__init__.py` with a `PipelineSpec`:

| Field | Meaning |
| --- | --- |
| `name` | Stable id, e.g. `asr`. Must match the `derived/<name>/` output prefix. |
| `description` | One-line human description shown in `tools/run_pipeline.py --help`. |
| `inputs` | Accepted input shapes — MIME strings (`audio/wav`, `text/plain`) or filename conventions (`transcript.json`, `text.clean.txt`). Documentation only; not enforced at runtime. |
| `outputs` | File **basenames** the pipeline writes (`transcript.json`, `clean.txt`, `index.json`, `moderation.json`) plus the matching `*.descriptor.json`. |
| `dependencies` | Third-party Python packages required at runtime, as pip specifiers (`faster-whisper>=1.0`, `sentence-transformers>=2.7`, `jsonschema>=4.20`, …). Listed for documentation and validation only — they MUST NOT be imported at module top-level (lazy-import inside `run` only), so a missing optional dep doesn't break `--help`. |
| `output_pointer_template` | Where outputs go, relative to the record root, with `{stem}` placeholder (e.g. `derived/asr/{stem}.transcript.json`). **Enforced** by `tools/validate_pipelines.py` to start with `derived/<spec.name>/`. |
| `register` / `run` | Lifecycle callbacks; `register(parser)` adds CLI flags, `run(args)` is the CLI entrypoint. |

The contract is enforced at static-validation time, not runtime, so a regression that adds a hosted-API call or a non-`derived/<name>/` output path fails in CI before any pipeline executes. See `tools/validate_pipelines.py`.

### The offline-first invariant

`tools/validate_pipelines.py` walks every `pipelines/**/*.py` file and refuses to merge any module that imports a hosted-API client (`openai`, `anthropic`, `google.generativeai`, `cohere`, `aliyun_sdk_bailian`, …). This is what turns "v0.5 is offline-first" from documentation into machine-checked policy. Every pipeline's descriptor mirrors this in JSON: `model.online_api_used` is always `false` when the model block is set.

### The descriptor (issue #35)

`pipelines/_descriptor.py` builds a JSON document for each output that records *who/what/where/with-what-hashes* — the full provenance. The schema (`schemas/derived-asset.schema.json`) requires:

- `schema_version` — pinned to `dlrs-derived-asset/1.0`.
- `derived_id` — ULID or UUIDv4. Once written it MUST NOT change; re-running the pipeline produces a *new* `derived_id` even if the inputs are byte-identical, so historical descriptors stay attributable.
- `record_id` — copied from `manifest.json`, so a descriptor is meaningful even if it leaks out of its record.
- `pipeline` — top-level string, one of `asr | text | vectorization | moderation | custom`. Must equal a registered `PipelineSpec.name`.
- `pipeline_version` — implementation version (SemVer or short commit SHA, e.g. `0.5.0` or `git:108b50c`). Combined with `inputs.inputs_hash` to decide whether a re-run is necessary.
- `created_at` — ISO 8601 UTC; the time of write, not the time the run started.
- `actor_role` — who triggered the run; mirrors the audit-event `actor_role` enum so `emit_audit_event.py` can quote it directly.
- `inputs.source_pointers[]` — relative paths (from the record root) to every pointer.json or raw artefact consumed. Pointer files are preferred so the hash check survives a storage migration.
- `inputs.inputs_hash` — `sha256:<hex>` of the canonical concatenation of input file content hashes. Pipelines MUST refuse to re-emit an identical descriptor if `inputs_hash` and `pipeline_version` both match.
- `inputs.preprocessing` — optional free-form record of pre-pipeline transforms (resampling, NFKC, …).
- `output.path` — relative path from the record root, MUST start with `derived/<pipeline>/`.
- `output.outputs_hash` — `sha256:<hex>` of the produced file's bytes (or, for multi-file outputs like a Qdrant collection, of the canonical manifest of those files).
- `output.byte_size` — optional convenience field.
- `model` — optional `{id, version?, source?, online_api_used: false}`. **Required** for `pipeline ∈ {asr, vectorization}`. `online_api_used` is `const: false` in v0.5 — the offline-first invariant enforced as schema.
- `parameters` — pipeline-specific kwargs serialised verbatim (chunk size, language hint, embedding dim, lexicon path, …). Anything that influences the output MUST be recorded here so re-runs are reproducible.
- `audit_event_ref` — optional pointer (`audit/events.jsonl#L12`) into the build event log.
- `moderation_outcome` — only set by the moderation pipeline (or other pipelines whose output drives policy); one of `pass | flag | block`.

A descriptor is the smallest object you can hand to a downstream consumer (auditor, registry builder, RAG indexer) to convince them an artefact came from a real record + real input. The schema is intentionally minimal so growing it later is additive.

## 2. The four pipelines

### 2.1 `asr` — speech to transcript (issue #31)

Two backends:

- **`dummy`** (default for tests/demo) — deterministic transcript derived from `sha256(audio bytes)`. No model, no decoding. The transcript is a single segment whose text is `dummy-asr/<sha-prefix>`. Used to unit-test downstream pipelines without bringing in `faster-whisper` and a 200 MB model on every CI run.
- **`faster-whisper`** — opt-in real backend. Lazy-imported only inside `_run()` so a missing optional dep doesn't break `pipelines.asr` import. Honours `--model` (default `small`, multilingual; `tiny` / `base` / `medium` / `large-v3` also accepted), `--language` (ISO-639-1 hint, auto-detect when omitted), and `--device` (`cpu` / `cuda`). On `cpu` it runs `int8` quantisation by default; this is what fits inside CI runners and developer laptops.

CLI:

```bash
python tools/run_pipeline.py asr \
  --record path/to/record \
  [--input artifacts/raw/audio/voice.wav] \
  [--backend dummy|faster-whisper] [--model tiny.en] [--device cpu|cuda] \
  [--output-dir DIR]
```

Output: `derived/asr/<stem>.transcript.json` (`{backend, model_id, segments: [{start, end, text}]}`) plus a descriptor.

The default audio resolution rule, when `--input` is not given: walk `manifest.artifacts[]` for the first entry with `kind == "audio"`; if it has a `path`, resolve it relative to the record root and use it. If no manifest match resolves, fall back to a sorted glob of `<record>/artifacts/**/*.{wav,mp3,m4a,flac}` and pick the first hit.

### 2.2 `text` — normalise + redact (issue #32)

Reads either a transcript JSON (auto-flattens `segments[].text`) or a plain `.txt`. Two transformations:

1. **Normalisation** — Unicode NFKC, strips zero-width / BOM characters, collapses whitespace, normalises smart quotes/dashes to ASCII, and applies the small bidi safeguard against text that mixes RTL/LTR through invisible markers. Determined by `--mode normalize`.
2. **Redaction** — conservative regex pattern set evaluated in priority order so specific patterns win over generic ones: `url_with_credentials` (`<URL_WITH_CREDENTIALS>`), `email` (`<EMAIL>`), `id_cn` (18-digit CN ID with terminal `\d|X|x`, `<ID_CN>`), `phone_cn` (`1[3-9]\d{9}`, `<PHONE_CN>`), `ipv4` (RFC-shape, `<IPV4>`), `credit_card_like` (13–19 digit runs with optional spaces / dashes, `<CARD>`), `phone_generic` (loose `+?\d[\d \-().]{6,18}\d`, `<PHONE>`). Replaced in-place with the **stable category placeholder** shown in parentheses — not the rule name and not the matched substring. Determined by `--mode redact`.

`--mode both` (default) runs normalise → redact in that order, so redaction patterns can rely on the post-NFKC encoding.

CLI:

```bash
python tools/run_pipeline.py text \
  --record path/to/record \
  [--input derived/asr/voice.transcript.json | path/to/text.txt] \
  [--mode normalize|redact|both] \
  [--output-dir DIR]
```

Outputs: `derived/text/<stem>.clean.txt` (the cleaned text), `<stem>.redactions.json` (one entry per substitution: `rule_name`, `start`, `end`, `replacement` — never the matched substring), and a descriptor. The redactions sidecar is what makes the normalisation diff auditable without re-leaking the data we just stripped.

### 2.3 `vectorization` — chunk + embed (issue #33)

Reads cleaned text. Chunking uses paragraph boundaries (`\n\n`) and slides a window of `--max-chars` (default 600) with `--overlap-chars` (default 80) across long paragraphs. Each chunk carries absolute character offsets that round-trip into the source: `clean_text[chunk.start:chunk.end] == chunk.text`.

Two backends:

- **`hash`** (default in tests) — deterministic 64-D vectors from `sha256(chunk_id || chunk_text)`. Vectors are unit-normalised so cosine works; collisions are vanishingly rare for the kind of chunks we see. Real for hashing-based ANN exploration; not real for semantic similarity.
- **`sentence-transformers`** — opt-in real backend. Default model `all-MiniLM-L6-v2` (384-D, ~80 MB cached). Lazy-imported inside `embed()`. Honours `--model` and `--device`.

Optional Qdrant push: `--qdrant-url http://127.0.0.1:6333` will, on top of writing `index.json`, upsert each chunk to a collection named after `record_id` (overridable via `--collection`). The Qdrant payload carries `record_id`, source pointer, char span, text-excerpt sha256, **`backend`**, and **`model_id`** (the v0.5 fix from PR #44 — these are stored as separate keys so downstream filters like `backend == "hash"` work without ambiguity).

CLI:

```bash
python tools/run_pipeline.py vectorization \
  --record path/to/record \
  [--input derived/text/voice.clean.txt] \
  [--backend hash|sentence-transformers] [--model all-MiniLM-L6-v2] [--device cpu|cuda] \
  [--max-chars 600] [--overlap-chars 80] \
  [--qdrant-url URL] [--collection NAME] \
  [--output-dir DIR]
```

Output: `derived/vectorization/<stem>.index.json` (`{backend, model_id, dim, entries: [{chunk_id, char_start, char_end, text_sha256, vector}]}`) plus a descriptor.

### 2.4 `moderation` — deterministic policy scan (issue #34)

Reads cleaned text, runs a regex/wordlist policy, writes a flag list and an outcome.

The built-in v0.5 policy is intentionally narrow:

| Rule | Severity |
| --- | --- |
| `self_harm_intent_en` | high |
| `violence_threat_en` | high |
| `pii_email_residual` | medium |
| `pii_phone_cn_residual` | medium |
| `profanity_basic_en` | low |

PII residual rules exist as a backstop in case a user runs `moderation` directly on raw text (skipping `text`). Richer multilingual / culturally-specific lists are loaded via `--policy-file FILE` (JSON, or YAML if PyYAML is installed). `--no-builtin` without a `--policy-file` is rejected so "no rules at all" is never silently a `pass`.

Outcome aggregation:

- `high` severity flag anywhere → **`block`**
- otherwise `medium` severity flag anywhere → **`flag`**
- otherwise → **`pass`**

The `moderation.json` artefact carries `rule_name`, `category`, `severity`, and `start`/`end` for each flag — **never** the matched substring. The unit test `tools/test_moderation_pipeline.py` asserts this property explicitly, so the moderation file itself cannot become a leak vector for the content it's flagging.

CLI:

```bash
python tools/run_pipeline.py moderation \
  --record path/to/record \
  [--input derived/text/voice.clean.txt] \
  [--policy-file PATH] [--no-builtin] \
  [--output-dir DIR]
```

Output: `derived/moderation/<stem>.moderation.json` (`{policy, version, outcome, summary, flags[]}`) plus a descriptor whose `moderation_outcome` mirrors the JSON outcome.

## 3. Running pipelines

### 3.1 In a record (recommended)

```bash
# from the repo root
python tools/run_pipeline.py asr           --record path/to/record
python tools/run_pipeline.py text          --record path/to/record
python tools/run_pipeline.py vectorization --record path/to/record
python tools/run_pipeline.py moderation    --record path/to/record
```

`run_pipeline.py` is the single entrypoint. Every pipeline is `python tools/run_pipeline.py <name>`; subcommands are listed by `python tools/run_pipeline.py --help`.

### 3.2 End-to-end demo

`examples/asr-demo/` is the canonical end-to-end fixture. `bash examples/asr-demo/run_demo.sh` regenerates a deterministic placeholder WAV (DLRS is pointer-first, so audio is never committed) and walks all four pipelines. See `examples/asr-demo/README.md` for the full walkthrough and the `REAL_ASR=1` / `REAL_EMBED=1` opt-in flags.

### 3.3 Stand-alone (no record)

Each pipeline also accepts an absolute `--input` and a `--output-dir`, so you can run any single stage on a one-off file:

```bash
python tools/run_pipeline.py text \
  --input ~/scratch/transcript.txt \
  --output-dir ~/scratch/cleaned/
```

When `--record` is absent, the descriptor's `record_id` falls back to `dlrs_unknown` (which still satisfies the schema's `^dlrs_[a-zA-Z0-9_-]{4,}$` pattern) and the offline-first invariant still applies.

## 4. Authoring a new pipeline

1. Create `pipelines/<name>/__init__.py`. Implement a `_run(args)` function.
2. Register a `PipelineSpec(name="<name>", inputs=[...], outputs=[...], dependencies=[...], output_pointer_template="derived/<name>/...", register=..., run=_run)` in `pipelines/__init__.py`.
3. Build descriptors with `pipelines._descriptor.DescriptorBuilder` so they validate against `schemas/derived-asset.schema.json` without per-pipeline boilerplate.
4. Add a `tools/test_<name>_pipeline.py` with at least: a unit test of the core transformation, a leak-guard test if your pipeline produces a redacted/flagged artefact, and an end-to-end CLI test against a synthetic record. Returning 0/1 from `main()` is enough — `tools/test_pipelines.py` runs the script as a subprocess.
5. Lazy-import any heavy dependency inside `_run()` (or a helper called from `_run()`), never at module top-level. Add the dependency to `tools/requirements.txt` only if it's truly always needed; otherwise document the opt-in in this guide and the pipeline's CLI `--help`.
6. Run `python tools/validate_pipelines.py` and `python tools/batch_validate.py`. Both must pass.

The hosted-API import guard will reject your pipeline at validation time if you accidentally `import openai` (or any of the listed hosted clients) anywhere in the file. Local clients like `qdrant_client` are explicitly allowed because Qdrant runs in a container the user hosts.

## 5. What v0.5 deliberately is not

- **Not a managed service.** v0.5 ships the libraries, not the daemon. Multi-tenant orchestration is v0.7.
- **Not a benchmark suite.** The `dummy` and `hash` backends are designed for reproducible CI; their numbers carry no semantic meaning. Real benchmarks belong in v0.6 alongside GraphRAG.
- **Not a hosted-API integration layer.** The whole point of v0.5 is that everything still works without one. v0.6 introduces an *opt-in* hosted-API backend behind the same `Policy` / `EmbeddingBackend` interfaces; the offline-first invariant stays the default.
- **Not a replacement for `validate_repo.py`.** Pipelines write derived data; they do not own the manifest or pointer schemas. Manifest validation, sensitive-file checks, and registry generation remain in the v0.3/v0.4 validators.

## 6. References

- Issue #28 — v0.5 offline-first epic.
- `pipelines/__init__.py` — pipeline registry.
- `tools/validate_pipelines.py` — static guard (offline-first + output-prefix invariant).
- `tools/test_pipelines.py` — umbrella test driver used by CI's `pipelines` job.
- `schemas/derived-asset.schema.json` — descriptor schema.
- `examples/asr-demo/` — end-to-end fixture.
- `docs/COMPLIANCE_CHECKLIST.md` — cross-references to PIPL / GDPR / EU AI Act / 中国深度合成办法.
