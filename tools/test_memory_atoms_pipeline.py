#!/usr/bin/env python3
"""Tests for ``pipelines.memory_atoms``.

Two layers, mirroring ``test_text_pipeline.py``:

1. Unit tests for :func:`pipelines.memory_atoms.extract.extract_paragraph_atoms`
   so behavioural regressions in the deterministic backend land here first.
2. End-to-end CLI tests that run ``run_pipeline.py memory_atoms`` against a
   synthetic record (one with a ``derived/text/<stem>.clean.txt`` source,
   one with a raw ``.txt`` artefact source) and validate the produced
   atoms file against ``schemas/memory-atom.schema.json`` plus the
   accompanying descriptor against ``schemas/derived-asset.schema.json``.

The spaCy backend is exercised with a unit test only when spaCy happens
to be importable; it is skipped (and the test still passes) otherwise so
that CI on a bare Python install is not blocked on an opt-in dependency.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipelines.memory_atoms.extract import (  # noqa: E402
    extract_paragraph_atoms,
    extract_spacy_atoms,
)

DERIVED_SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"
ATOM_SCHEMA_PATH = ROOT / "schemas" / "memory-atom.schema.json"


def _assert(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _unit_tests_paragraph_backend(errors: list[str]) -> None:
    text = "Para one line one.\nPara one line two.\n\n\nPara two only line.\n\nPara three."
    atoms = extract_paragraph_atoms(
        text=text,
        record_id="dlrs_test_lin",
        source_pointer="derived/text/sample.clean.txt",
        sensitivity="S1_INTERNAL",
        erasable=True,
        pipeline_version="0.6.0",
    )
    _assert(len(atoms) == 3, f"paragraph: expected 3 atoms, got {len(atoms)}", errors)
    if not atoms:
        return
    a0 = atoms[0]
    _assert(a0["redaction_safe"] is True, "paragraph: redaction_safe must be true", errors)
    _assert(a0["sensitivity"] == "S1_INTERNAL", "paragraph: sensitivity not propagated", errors)
    _assert(a0["erasable"] is True, "paragraph: erasable not propagated", errors)
    _assert(0 <= a0["confidence"] <= 1, "paragraph: confidence out of range", errors)
    _assert(a0["pipeline_version"] == "0.6.0", "paragraph: pipeline_version mismatch", errors)
    _assert(a0["text"].startswith("Para one"), f"paragraph: unexpected first atom text: {a0['text']!r}", errors)
    # atom_ids must be unique across atoms in the same run
    ids = [a["atom_id"] for a in atoms]
    _assert(len(set(ids)) == len(ids), f"paragraph: atom_ids not unique: {ids}", errors)

    # empty / whitespace-only text -> zero atoms
    empty = extract_paragraph_atoms(
        text="\n\n\n   \n\n",
        record_id="dlrs_test_lin",
        source_pointer="derived/text/sample.clean.txt",
        sensitivity="S0_PUBLIC",
        erasable=True,
        pipeline_version="0.6.0",
    )
    _assert(empty == [], f"paragraph: empty input must produce no atoms, got {empty}", errors)


def _unit_tests_spacy_backend(errors: list[str]) -> None:
    try:
        import spacy  # type: ignore  # noqa: F401
    except ImportError:
        # spaCy is opt-in. Skip silently rather than fail the test so CI on
        # a bare Python install passes; a separate env where spacy is
        # present will exercise this branch.
        print("    [skip] spacy not installed; skipping spacy backend unit test")
        return

    text = "First sentence here. Second one follows! Third one too?"
    atoms = extract_spacy_atoms(
        text=text,
        record_id="dlrs_test_lin",
        source_pointer="derived/text/sample.clean.txt",
        sensitivity="S1_INTERNAL",
        erasable=False,
        pipeline_version="0.6.0",
    )
    _assert(len(atoms) >= 2, f"spacy: expected at least 2 atoms, got {len(atoms)}", errors)
    if atoms:
        _assert(atoms[0]["erasable"] is False, "spacy: erasable=false not propagated", errors)


def _validate_atom_jsonl(atoms_path: Path, errors: list[str]) -> int:
    from jsonschema import Draft202012Validator

    schema = json.loads(ATOM_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    n = 0
    for line in atoms_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        n += 1
        atom = json.loads(line)
        validation_errors = list(validator.iter_errors(atom))
        if validation_errors:
            errors.append(
                f"atoms[{n - 1}] failed schema: " + "; ".join(e.message for e in validation_errors[:3])
            )
    return n


def _validate_descriptor_against_schema(descriptor_path: Path, errors: list[str]) -> dict:
    from jsonschema import Draft202012Validator

    schema = json.loads(DERIVED_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    validation_errors = list(validator.iter_errors(descriptor))
    if validation_errors:
        errors.append(
            f"descriptor failed derived-asset schema: " + "; ".join(e.message for e in validation_errors[:3])
        )
    return descriptor


def _e2e_against_clean_text(errors: list[str]) -> None:
    """Synthesize a record with derived/text/sample.clean.txt and run the pipeline."""
    with tempfile.TemporaryDirectory() as tmp:
        record = Path(tmp) / "rec"
        (record / "derived" / "text").mkdir(parents=True, exist_ok=True)
        (record / "manifest.json").write_text(
            json.dumps({"record_id": "dlrs_e2e_lin"}), encoding="utf-8"
        )
        (record / "derived" / "text" / "sample.clean.txt").write_text(
            "First paragraph from a cleaned source.\n\n"
            "Second paragraph; this one mentions <EMAIL> as a placeholder.\n\n"
            "Third one.",
            encoding="utf-8",
        )

        cmd = [
            sys.executable,
            str(ROOT / "tools" / "run_pipeline.py"),
            "memory_atoms",
            "--record",
            str(record),
            "--sensitivity",
            "S1_INTERNAL",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        if proc.returncode != 0:
            errors.append(f"e2e clean.txt: cli exited {proc.returncode}\nstderr={proc.stderr}")
            return

        atoms_path = record / "derived" / "memory_atoms" / "sample.atoms.jsonl"
        descriptor_path = record / "derived" / "memory_atoms" / "sample.atoms.descriptor.json"
        _assert(atoms_path.exists(), f"e2e clean.txt: missing {atoms_path}", errors)
        _assert(descriptor_path.exists(), f"e2e clean.txt: missing {descriptor_path}", errors)
        if atoms_path.exists():
            n = _validate_atom_jsonl(atoms_path, errors)
            _assert(n == 3, f"e2e clean.txt: expected 3 atoms, got {n}", errors)
        if descriptor_path.exists():
            descriptor = _validate_descriptor_against_schema(descriptor_path, errors)
            _assert(
                descriptor.get("output", {}).get("path", "").startswith("derived/memory_atoms/"),
                "e2e clean.txt: descriptor output path must be under derived/memory_atoms/",
                errors,
            )
            _assert(
                descriptor.get("pipeline") == "memory_atoms",
                f"e2e clean.txt: descriptor.pipeline mismatch: {descriptor.get('pipeline')}",
                errors,
            )


def _e2e_against_raw_text_with_pii(errors: list[str]) -> None:
    """Run against a raw .txt artefact containing PII; the pipeline must
    re-redact before emitting atoms (so the atom text contains the
    placeholder, not the original substring)."""
    with tempfile.TemporaryDirectory() as tmp:
        record = Path(tmp) / "rec"
        (record / "artifacts" / "raw" / "text").mkdir(parents=True, exist_ok=True)
        (record / "manifest.json").write_text(
            json.dumps({"record_id": "dlrs_e2e_pii"}), encoding="utf-8"
        )
        raw_text = (
            "Reach me at alice@example.com any time.\n\n"
            "Phone backup is 13912345678 if email fails."
        )
        (record / "artifacts" / "raw" / "text" / "diary.txt").write_text(
            raw_text, encoding="utf-8"
        )

        cmd = [
            sys.executable,
            str(ROOT / "tools" / "run_pipeline.py"),
            "memory_atoms",
            "--record",
            str(record),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        if proc.returncode != 0:
            errors.append(f"e2e raw.txt: cli exited {proc.returncode}\nstderr={proc.stderr}")
            return

        atoms_path = record / "derived" / "memory_atoms" / "diary.atoms.jsonl"
        if not atoms_path.exists():
            errors.append(f"e2e raw.txt: missing {atoms_path}")
            return

        text_blob = atoms_path.read_text(encoding="utf-8")
        _assert(
            "alice@example.com" not in text_blob,
            "e2e raw.txt: original email leaked into atoms.jsonl (redactor not re-applied?)",
            errors,
        )
        _assert(
            "13912345678" not in text_blob,
            "e2e raw.txt: original phone leaked into atoms.jsonl",
            errors,
        )
        _assert("<EMAIL>" in text_blob, "e2e raw.txt: <EMAIL> placeholder missing", errors)
        _assert("<PHONE_CN>" in text_blob, "e2e raw.txt: <PHONE_CN> placeholder missing", errors)


def main() -> int:
    try:
        from jsonschema import Draft202012Validator  # noqa: F401
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    errors: list[str] = []
    print("test_memory_atoms_pipeline: unit/paragraph")
    _unit_tests_paragraph_backend(errors)
    print("test_memory_atoms_pipeline: unit/spacy")
    _unit_tests_spacy_backend(errors)
    print("test_memory_atoms_pipeline: e2e clean.txt input")
    _e2e_against_clean_text(errors)
    print("test_memory_atoms_pipeline: e2e raw.txt input with PII (redactor re-applied)")
    _e2e_against_raw_text_with_pii(errors)

    if errors:
        print(f"\ntest_memory_atoms_pipeline: {len(errors)} failure(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\ntest_memory_atoms_pipeline: all assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
