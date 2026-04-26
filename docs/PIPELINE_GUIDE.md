# DLRS v0.6 Pipeline Guide

> Companion to `examples/asr-demo/README.md` (v0.5) and `examples/memory-graph-demo/README.md` (v0.6). The demos answer *"can I run it?"*; this guide answers *"how is it built and what guarantees can I rely on?"*.

DLRS v0.5 introduced four offline-first build pipelines that turn raw artefacts referenced by a record into derived assets fit for downstream consumption (registry display, RAG, moderation review). DLRS v0.6 adds two more (memory atoms, knowledge graph), wires every descriptor into the audit log via a mechanical bridge, and provides an opt-in policy gate for the *one* future case where a record explicitly authorises a hosted-API code path. All six pipelines share the same contract, the same provenance descriptor, and the same hard offline-first default — they exist primarily to keep the rest of DLRS honest about *where* its derived data comes from.

## 0. Mental model

```
record/
├── manifest.json
├── public_profile.json
├── artifacts/raw_pointers/audio/voice.pointer.json   # or repo://artifacts/raw/audio/voice.wav
├── audit/events.jsonl                         # hash-chained audit log (v0.4+)
├── policy/hosted_api.json                     # OPTIONAL — opt-in hosted-API policy (v0.6)
└── derived/
    ├── asr/voice.transcript.json              # pipeline: asr
    ├── asr/voice.transcript.descriptor.json
    ├── text/voice.clean.txt                   # pipeline: text
    ├── text/voice.redactions.json
    ├── text/voice.clean.descriptor.json
    ├── vectorization/voice.index.json         # pipeline: vectorization
    ├── vectorization/voice.index.descriptor.json
    ├── moderation/voice.moderation.json       # pipeline: moderation
    ├── moderation/voice.moderation.descriptor.json
    ├── memory_atoms/voice.atoms.jsonl         # pipeline: memory_atoms (v0.6)
    ├── memory_atoms/voice.atoms.descriptor.json
    ├── knowledge_graph/voice.nodes.jsonl      # pipeline: knowledge_graph (v0.6)
    ├── knowledge_graph/voice.edges.jsonl
    └── knowledge_graph/voice.graph.descriptor.json
```

The v0.5 chain is `audio → asr → text → {vectorization, moderation}`. The v0.6 chain extends it via `text → memory_atoms → knowledge_graph`. Each step writes its output under `derived/<pipeline-name>/` and a sibling `<stem>.descriptor.json` provenance file that **always** validates against `schemas/derived-asset.schema.json`. v0.6 adds: each descriptor write is mirrored as one `derived_asset_emitted` event in `audit/events.jsonl`, hash-chained into the existing audit log.

You do not have to run all six. Each pipeline accepts an explicit `--input` so the chain can be entered at any stage, and `--no-audit` lets fixture / dry-run invocations skip the audit bridge entirely.

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

`tools/validate_pipelines.py` walks every `pipelines/**/*.py` file and refuses to merge any module that imports a hosted-API client (`openai`, `anthropic`, `google.generativeai`, `cohere`, `aliyun_sdk_bailian`, …). This is what turns "DLRS is offline-first by default" from documentation into machine-checked policy. Every pipeline's descriptor mirrors this in JSON: `model.online_api_used` is always `false` when the model block is set.

v0.6 keeps the static guard *unchanged*. The opt-in hosted-API policy gate (see §4) does **not** relax the import ban; pipelines that need a hosted backend lazy-import the SDK via `importlib.import_module(...)` *inside* a branch already guarded by `pipelines._hosted_api.assert_allowed(...)`. There is still no way to ship a hosted-API code path that runs without an explicit per-record policy.

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

Outputs: `derived/text/<stem>.clean.txt` (the cleaned text), `<stem>.redactions.json` (one entry per substitution: `kind`, `start`, `end`, `replacement` — where `kind` is the rule name like `email` or `phone_cn`, never the matched substring), and a descriptor. The redactions sidecar is what makes the normalisation diff auditable without re-leaking the data we just stripped.

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

*(memory_atoms — §2.5 — and knowledge_graph — §2.6 — pick up after this section.)*


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

The `moderation.json` artefact carries `rule`, `category`, `severity`, and `start`/`end` for each flag — **never** the matched substring. The unit test `tools/test_moderation_pipeline.py` asserts this property explicitly, so the moderation file itself cannot become a leak vector for the content it's flagging.

CLI:

```bash
python tools/run_pipeline.py moderation \
  --record path/to/record \
  [--input derived/text/voice.clean.txt] \
  [--policy-file PATH] [--no-builtin] \
  [--output-dir DIR]
```

Output: `derived/moderation/<stem>.moderation.json` (`{policy, version, outcome, summary, flags[]}`) plus a descriptor whose `moderation_outcome` mirrors the JSON outcome.

### 2.5 `memory_atoms` — paragraph / sentence atomisation (issue #56)

Reads cleaned text and produces line-delimited memory atom records suitable for downstream RAG, recall, and lifecycle marking. v0.6 introduces this stage so the rest of v0.6 (knowledge graph, future episodic recall) has a stable input format.

Two backends:

- **`paragraph`** (default, dependency-free) — splits on blank-line boundaries; one atom per paragraph. Deterministic, byte-stable across reruns.
- **`spacy`** — opt-in, sentence-granular. Lazy-imported. Requires `pip install spacy` plus a model (`python -m spacy download en_core_web_sm`). Honours `--spacy-model`.

Each atom carries: `atom_id` (ULID), `record_id`, `source_pointer` (relative path back to the cleaned text), absolute char-offsets that round-trip into the source (`clean_text[atom.char_start:atom.char_end] == atom.text`), creation time, and `sensitivity` (defaults to `S1_INTERNAL`; override per-record via `--sensitivity`). The schema is `schemas/memory-atom.schema.json` (13 fields, 11 required, `additionalProperties: false`); see #54 for the full field list.

CLI:

```bash
python tools/run_pipeline.py memory_atoms \
  --record path/to/record \
  [--input derived/text/voice.clean.txt] \
  [--backend paragraph|spacy] [--spacy-model en_core_web_sm] \
  [--sensitivity S0_PUBLIC|S1_INTERNAL|S2_CONFIDENTIAL|S3_BIOMETRIC|S4_RESTRICTED] \
  [--output-dir DIR] [--no-audit]
```

Output: `derived/memory_atoms/<stem>.atoms.jsonl` (one JSON atom per line) plus a single `<stem>.atoms.descriptor.json`. The descriptor's `parameters` records `backend`, `spacy_model` (when applicable), and the atom count.

Leak-safety: atoms carry the cleaned text *as-is*, so anything redacted by the v0.5 `text` pipeline stays redacted (the v0.5 redaction tokens like `<EMAIL>` are unchanged). `tools/test_memory_atoms_pipeline.py` asserts a leak-guard property: every atom string survives a regex scan for the v0.5 PII patterns and never reintroduces a raw match.

### 2.6 `knowledge_graph` — regex entity + co-mention edge extraction (issue #57)

Reads memory atoms (or any line-delimited JSON with `text` + `atom_id`) and emits a small co-mention knowledge graph: capitalised name candidates as nodes, atoms-in-common-as-co-mention as edges.

One backend (`regex`) by default. The candidate regex matches a capitalised word optionally followed by additional capitalised words (`Alice`, `Bob`, `European Commission`) using a literal space — never `\s+` — so labels never contain `\n` (the v0.6.1 fix from PR #71). Candidates are normalised (case-folded for de-dup) and filtered against a small stopword list shipped with the pipeline.

Node schema: `schemas/entity-graph-node.schema.json` (`node_id`, `record_id`, `label`, `entity_type`, `mention_count`, `source_atom_ids[]`, optional `metadata`). Edge schema: `schemas/entity-graph-edge.schema.json` (`edge_id`, `record_id`, `source_node_id`, `target_node_id`, `relation`, `weight`, `source_atom_ids[]`). Both are `additionalProperties: false`; see #55 for full field lists.

CLI:

```bash
python tools/run_pipeline.py knowledge_graph \
  --record path/to/record \
  [--input derived/memory_atoms/voice.atoms.jsonl] \
  [--sensitivity S0_PUBLIC|S1_INTERNAL|S2_CONFIDENTIAL|S3_BIOMETRIC|S4_RESTRICTED] \
  [--output-dir DIR] [--no-audit]
```

Output: `derived/knowledge_graph/<stem>.nodes.jsonl`, `<stem>.edges.jsonl`, and a single `<stem>.graph.descriptor.json` whose `output.path` points at the nodes file (with `parameters.edges_path` recording the edges sibling). The descriptor's `parameters` includes node count, edge count, and the regex's commit-pinned identifier so reruns are reproducible.

Leak-safety: nodes carry only the matched label, not the surrounding atom text. `source_atom_ids[]` is an indirection, not the original text; resolving it requires read access to `derived/memory_atoms/`.

## 3. Descriptor → audit/events.jsonl bridge (issue #58)

v0.6 wires every descriptor write into the v0.4 hash-chained audit log. After a pipeline finishes its descriptor (and after `tools/validate_pipelines.py` would have run on it), `pipelines._audit_bridge.maybe_bridge` does three things:

1. Appends a `derived_asset_emitted` event to `audit/events.jsonl` carrying `pipeline`, `record_id`, the descriptor's `derived_id`, and the descriptor's `output.outputs_hash`.
2. Reuses the v0.4 emitter (`tools/emit_audit_event.py`) so the new event participates in the same hash chain — `prev_hash` of event N = `hash` of event N-1, with the genesis event's `prev_hash` set to `null`. The bridge introduces no new chain semantics.
3. Back-fills the descriptor's `audit_event_ref` field with `audit/events.jsonl#L<n>` — a stable pointer back into the chain — so reviewers can pivot from artefact → authorisation in one click.

`derived_asset_emitted` is the 9th value in `schemas/audit-event.schema.json::event_type.enum`; the eight v0.4 lifecycle events are unchanged, and the enum is still closed via `additionalProperties: false`.

The bridge is a deliberately thin module so pipelines can opt out:

- `--no-audit` on any pipeline CLI suppresses the bridge call site (the descriptor is still emitted, just without an audit-log mirror). Used by fixtures, dry-runs, and the unit tests for #58.
- If the record has no `manifest.json` (e.g., a stand-alone `--input` / `--output-dir` run with no enclosing record), the bridge is a silent no-op; there is no error and no event.

The regression test for the bridge is `tools/test_descriptor_audit_bridge.py`, run as one of the cross-cutting tests inside `tools/test_pipelines.py`. It covers: event append + schema compliance, hash chaining across two pipelines, descriptor back-fill, `--no-audit` skip, and silent-no-op without a manifest.

## 4. Hosted-API opt-in policy gate (issue #59)

DLRS is offline-first by default. v0.5 enforced this with the static `validate_pipelines.py` import ban; v0.6 keeps that ban and adds a *narrow* mechanism for opting back in, per-record, without weakening the default.

A pipeline that wants to call a hosted API must:

1. **Read the record's policy file.** The data subject (or their authorised agent) commits `<record>/policy/hosted_api.json`, validated against `schemas/hosted-api-policy.schema.json`. Required fields: `schema_version`, `opt_in: bool`, `allowed_providers[]` (drawn from a closed enum: `openai`, `anthropic`, `google_generativeai`, `cohere`, `deepl`, `replicate`, `aliyun_bailian`, `azure_openai`, `aws_bedrock`, `custom`), `allowed_pipelines[]` (snake_case names matching `PipelineSpec.name`), `consent_evidence_ref`, `issued_at`, `expires_at`. Optional: `data_residency`, `notes`, `rate_limits`. `additionalProperties: false`.
2. **Gate the call site.** Any hosted-API code path goes inside:
   ```python
   from pipelines._hosted_api import assert_allowed
   assert_allowed(record_root, pipeline_name="vectorization", provider="openai")
   sdk = importlib.import_module("openai")  # lazy-import inside the gate
   ```
   `assert_allowed` raises `HostedApiNotAllowed` unless every check passes:
   - policy file exists
   - `opt_in is True`
   - `provider in allowed_providers`
   - `pipeline_name in allowed_pipelines`
   - `issued_at <= now < expires_at` (half-open window; `expires_at` denies, `issued_at` permits)
3. **Static guard stays on.** Because the SDK is `importlib`'d *inside* the gated branch, `tools/validate_pipelines.py` continues to refuse anything unconditional. The combination — static ban + per-record runtime gate + lazy import — is what makes "DLRS authorises a hosted call" auditable.

`load_policy(record_root)` returns `None` when the policy file is absent (default-deny path); it raises `HostedApiNotAllowed` if the file is present but malformed (invalid JSON, schema violation, `expires_at <= issued_at`). `list_allowed_providers(policy)` is a convenience for `--show-policy`-style CLIs.

v0.6 ships the gate but **does not** wire any pipeline to actually call a hosted API. That decision is deferred to v0.7 (or the first sub-PR that needs it) so reviewers can assess the policy contract on its own merits. The audit bridge composes cleanly: a pipeline that successfully passes `assert_allowed` should record a `derived_asset_emitted` audit event whose `metadata.hosted_provider` field captures the provider used; that field is reserved but unwritten in v0.6.

The regression test for the gate is `tools/test_hosted_api_policy.py`, run as one of the cross-cutting tests inside `tools/test_pipelines.py`. It covers: schema golden + 6 negative schema cases (missing fields, drift, unknown provider, uppercase pipeline name, opt_in not bool, additionalProperties), default-deny, `opt_in=false`, provider whitelist, pipeline whitelist, time bounds (before `issued_at` / after `expires_at`), `expires_at <= issued_at`, malformed JSON, and `list_allowed_providers` consistency.

## 5. Running pipelines

### 5.1 In a record (recommended)

```bash
# from the repo root
python tools/run_pipeline.py asr             --record path/to/record
python tools/run_pipeline.py text            --record path/to/record
python tools/run_pipeline.py vectorization   --record path/to/record
python tools/run_pipeline.py moderation      --record path/to/record
python tools/run_pipeline.py memory_atoms    --record path/to/record
python tools/run_pipeline.py knowledge_graph --record path/to/record
```

`run_pipeline.py` is the single entrypoint. Every pipeline is `python tools/run_pipeline.py <name>`; subcommands are listed by `python tools/run_pipeline.py --help`.

### 5.2 End-to-end demos

- `examples/asr-demo/` (v0.5) is the canonical audio chain fixture. `bash examples/asr-demo/run_demo.sh` regenerates a deterministic placeholder WAV (DLRS is pointer-first, so audio is never committed) and walks ASR → text → vectorization → moderation. See `examples/asr-demo/README.md` for the full walkthrough and the `REAL_ASR=1` / `REAL_EMBED=1` opt-in flags.
- `examples/memory-graph-demo/` (v0.6) is the canonical memory-graph chain fixture. `bash examples/memory-graph-demo/run_demo.sh` stages a fictional 3-paragraph diary excerpt and walks text → memory_atoms → knowledge_graph, then prints the resulting 3-event hash-chained audit log. See `examples/memory-graph-demo/README.md` for the walkthrough and the `REAL_ATOMS=1` opt-in for the spaCy backend.

### 5.3 Stand-alone (no record)

Each pipeline also accepts an absolute `--input` and a `--output-dir`, so you can run any single stage on a one-off file:

```bash
python tools/run_pipeline.py text \
  --input ~/scratch/transcript.txt \
  --output-dir ~/scratch/cleaned/
```

When `--record` is absent, the descriptor's `record_id` falls back to `dlrs_unknown` (which still satisfies the schema's `^dlrs_[a-zA-Z0-9_-]{4,}$` pattern) and the offline-first invariant still applies.

## 6. Authoring a new pipeline

1. Create `pipelines/<name>/__init__.py`. Implement a `_run(args)` function.
2. Register a `PipelineSpec(name="<name>", inputs=[...], outputs=[...], dependencies=[...], output_pointer_template="derived/<name>/...", register=..., run=_run)` in `pipelines/__init__.py`.
3. Build descriptors with `pipelines._descriptor.DescriptorBuilder` so they validate against `schemas/derived-asset.schema.json` without per-pipeline boilerplate.
4. After writing the descriptor, call `pipelines._audit_bridge.maybe_bridge(record_root, pipeline_name=..., descriptor=..., descriptor_path=..., skip=getattr(args, "no_audit", False))` so v0.6's descriptor → audit bridge picks up your pipeline automatically (see §3). Add `--no-audit` to your CLI parser via `parser.add_argument("--no-audit", action="store_true", help="...")`.
5. If your pipeline calls a hosted API, gate the call site with `pipelines._hosted_api.assert_allowed(record_root, pipeline_name=..., provider=...)` and lazy-import the SDK *inside* the gated branch via `importlib.import_module(...)`. Top-level `import openai` (or any hosted client) is rejected by `tools/validate_pipelines.py`. See §4 for the full contract.
6. Add a `tools/test_<name>_pipeline.py` with at least: a unit test of the core transformation, a leak-guard test if your pipeline produces a redacted/flagged artefact, and an end-to-end CLI test against a synthetic record. Returning 0/1 from `main()` is enough — `tools/test_pipelines.py` runs the script as a subprocess. Append the test to either `PER_PIPELINE_TESTS` (if it's a per-pipeline behaviour test) or `CROSS_CUTTING_TESTS` (if it spans multiple pipelines, like the audit bridge).
7. Lazy-import any heavy dependency inside `_run()` (or a helper called from `_run()`), never at module top-level. Add the dependency to `tools/requirements.txt` only if it's truly always needed; otherwise document the opt-in in this guide and the pipeline's CLI `--help`.
8. Run `python tools/validate_pipelines.py` and `python tools/batch_validate.py`. Both must pass.

The hosted-API import guard will reject your pipeline at validation time if you accidentally `import openai` (or any of the listed hosted clients) anywhere in the file. Local clients like `qdrant_client` are explicitly allowed because Qdrant runs in a container the user hosts.

## 7. What v0.6 deliberately is not

- **Not a managed service.** v0.6 still ships the libraries, not the daemon. Multi-tenant orchestration is v0.7.
- **Not a benchmark suite.** The `dummy`, `hash`, `paragraph`, and `regex` backends are designed for reproducible CI; their numbers carry no semantic meaning. Real benchmarks belong in v0.7 alongside the runtime layer.
- **Not a hosted-API integration layer.** v0.6 ships the policy gate (§4) but does not wire any pipeline to actually call a hosted API. The first hosted-API backend lands as a follow-up sub-PR and must compose with the gate; the offline-first default stays the default.
- **Not a replacement for the v0.4 audit emitter.** v0.6's bridge appends *one new event type* (`derived_asset_emitted`) to the existing hash-chained log. The eight v0.4 lifecycle events are unchanged; the v0.4 emitter remains the single point of write.
- **Not a replacement for `validate_repo.py`.** Pipelines write derived data; they do not own the manifest or pointer schemas. Manifest validation, sensitive-file checks, and registry generation remain in the v0.3/v0.4 validators.

## 8. References

- Issue [#28](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/28) — v0.5 offline-first epic.
- Issue [#52](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/52) — v0.6 memory atoms + knowledge graph + descriptor audit bridge epic.
- `pipelines/__init__.py` — pipeline registry.
- `pipelines/_descriptor.py` — shared descriptor builder.
- `pipelines/_audit_bridge.py` — v0.6 descriptor → `audit/events.jsonl` bridge.
- `pipelines/_hosted_api.py` — v0.6 hosted-API opt-in policy gate.
- `tools/validate_pipelines.py` — static guard (offline-first + output-prefix invariant).
- `tools/test_pipelines.py` — umbrella test driver used by CI's `pipelines` job (per-pipeline + cross-cutting).
- `schemas/derived-asset.schema.json` — descriptor schema.
- `schemas/audit-event.schema.json` — audit-event schema (extended with `derived_asset_emitted` in v0.6).
- `schemas/memory-atom.schema.json` — v0.6 memory atom schema.
- `schemas/entity-graph-node.schema.json` / `schemas/entity-graph-edge.schema.json` — v0.6 knowledge graph schemas.
- `schemas/hosted-api-policy.schema.json` — v0.6 hosted-API opt-in policy schema.
- `examples/asr-demo/` — v0.5 end-to-end fixture.
- `examples/memory-graph-demo/` — v0.6 end-to-end fixture.
- `docs/COMPLIANCE_CHECKLIST.md` — cross-references to PIPL / GDPR / EU AI Act / 中国深度合成办法.
