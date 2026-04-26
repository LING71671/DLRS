# Schemas

JSON Schemas used by DLRS validation tooling. All schemas use Draft 2020-12.

| File                              | Purpose                                                                                   |
| --------------------------------- | ----------------------------------------------------------------------------------------- |
| `manifest.schema.json`            | Top-level `manifest.json` for a single DLRS record. Required for every archive.            |
| `pointer.schema.json`             | Pointer files (`*.pointer.json`) for externally-stored artifacts. See `docs/OBJECT_STORAGE_POINTERS.md`. |
| `consent.schema.json`             | Consent metadata (mirrors `manifest.consent` and standalone `consent_metadata.json`).     |
| `public-profile.schema.json`      | Public-facing profile surfaced in the registry.                                           |
| `audit-event.schema.json`         | Append-only audit events.                                                                 |
| `derived-asset.schema.json`       | Provenance / lineage for artefacts produced by a build pipeline (ASR, text clean, embedding, moderation). |
| `registry-entry.schema.json`      | Output rows in `registry/humans.index.jsonl`.                                             |

Run `python tools/lint_schemas.py` to verify schema validity locally.
