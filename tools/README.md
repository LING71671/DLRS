# Tools

Python scripts that implement DLRS validation, registry generation, media
checks, and storage helpers. All tools are pure-Python and run from the
repository root unless noted otherwise.

```bash
python -m pip install -r tools/requirements.txt
```

## Validation

| Script                       | Purpose                                                                                  |
| ---------------------------- | ---------------------------------------------------------------------------------------- |
| `lint_schemas.py`            | Lints every `schemas/*.schema.json`. Required-key check and Draft 2020-12 validity.       |
| `validate_repo.py`           | Walks `humans/**/manifest.json` and runs schema + minimum-collection-standard checks.    |
| `validate_manifest.py`       | Validates a single `manifest.json` against `schemas/manifest.schema.json`.               |
| `validate_examples.py`       | Validates every `examples/*` archive (`manifest.json` + `public_profile.json`).          |
| `validate_media.py`          | Walks `*.pointer.json` files and enforces minimum media-collection thresholds.            |
| `check_sensitive_files.py`   | Refuses commits of raw audio/video/image/biometric files outside allowed paths.           |
| `test_registry.py`           | Unit tests for the public-registry inclusion / exclusion / data-integrity rules.          |

## Build / generation

| Script                       | Purpose                                                                                  |
| ---------------------------- | ---------------------------------------------------------------------------------------- |
| `build_registry.py`          | Generates `registry/humans.index.jsonl` and `registry/humans.index.csv`.                  |
| `new_human_record.py`        | Scaffolds a new `humans/.../<record_id>/` directory from `humans/_TEMPLATE/`.             |
| `i18n_helper.py`             | Helper for managing translation completeness.                                            |

## Storage / cost

| Script                       | Purpose                                                                                  |
| ---------------------------- | ---------------------------------------------------------------------------------------- |
| `upload_to_storage.py`       | Uploads a local asset to S3 / OSS / COS / MinIO and emits a DLRS pointer file.            |
| `estimate_costs.py`          | Estimates monthly storage + egress cost for the archives in this repo.                   |

## Recommended pre-commit invocation

```bash
python tools/check_sensitive_files.py
python tools/lint_schemas.py
python tools/validate_repo.py
python tools/validate_examples.py
python tools/validate_media.py
python tools/test_registry.py
python tools/build_registry.py
```

The same sequence runs in `.github/workflows/validate.yml` on every push and
pull request.
