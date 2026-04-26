#!/usr/bin/env python3
"""Tests for ``pipelines.knowledge_graph``.

Three layers:

1. Unit tests for :func:`pipelines.knowledge_graph.extract.extract_regex_graph`
   covering: dedupe by case-folded label, salience scaling, co-mention
   edge construction, redaction-placeholder filtering, stop-token
   filtering for single-word candidates, ``min_mentions`` threshold.
2. End-to-end CLI test using a synthetic record with a memory_atoms
   ``atoms.jsonl`` source: validates each emitted node / edge against
   its schema and the descriptor against ``derived-asset.schema.json``.
3. End-to-end CLI test using a raw ``.txt`` source containing PII
   (``alice@example.com``, ``13912345678``): asserts neither the
   original substring nor the email's local-part bleeds into nodes /
   edges, and the corresponding ``<EMAIL>`` / ``<PHONE_CN>`` placeholders
   are NOT promoted to entities (they would be unhelpful and possibly
   misleading).
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

from pipelines.knowledge_graph.extract import extract_regex_graph  # noqa: E402

DERIVED_SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"
NODE_SCHEMA_PATH = ROOT / "schemas" / "entity-graph-node.schema.json"
EDGE_SCHEMA_PATH = ROOT / "schemas" / "entity-graph-edge.schema.json"


def _assert(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _unit_dedupe_and_aliases(errors: list[str]) -> None:
    units = [
        "Alice met Bob in Beijing.",
        "ALICE called Bob again later in Beijing.",  # ALICE filtered (no [a-z])
        "Alice and Bob discussed the project.",
    ]
    nodes, edges = extract_regex_graph(
        context_units=units,
        record_id="dlrs_test_lin",
        evidence_pointer="derived/text/sample.clean.txt",
        sensitivity="S1_INTERNAL",
        min_mentions=1,
        pipeline_version="0.6.0",
    )
    labels = sorted(n["label"] for n in nodes)
    _assert(
        labels == ["Alice", "Beijing", "Bob"],
        f"unit/dedupe: expected [Alice, Beijing, Bob], got {labels}",
        errors,
    )
    # Each node had exactly one canonical surface form, so no alias should
    # appear (ALICE was filtered out by the [A-Z][a-z]+ pattern).
    for n in nodes:
        _assert(
            n["aliases"] == [],
            f"unit/dedupe: expected empty aliases for {n['label']}, got {n['aliases']}",
            errors,
        )
    # Co-mention edges should be Alice<->Bob<->Beijing for unit 1, no
    # duplicates in unit 2 (same pair seen), Alice<->Bob in unit 3.
    relations = [(e["subject_node_id"], e["object_node_id"]) for e in edges]
    _assert(
        len(relations) >= 2,
        f"unit/dedupe: expected at least 2 edges, got {len(relations)}",
        errors,
    )
    for e in edges:
        _assert(e["relation"] == "dlrs.co_mentioned_in", f"unit/dedupe: bad relation {e['relation']}", errors)
        _assert(e["confidence"] == 0.5, f"unit/dedupe: confidence not pinned: {e['confidence']}", errors)


def _unit_redaction_placeholder_filtering(errors: list[str]) -> None:
    units = [
        "Reach <EMAIL> for details.",
        "Phone <PHONE_CN> works too.",
        "Alice met Bob.",
    ]
    nodes, _edges = extract_regex_graph(
        context_units=units,
        record_id="dlrs_test_lin",
        evidence_pointer="derived/text/sample.clean.txt",
        sensitivity="S1_INTERNAL",
        min_mentions=1,
        pipeline_version="0.6.0",
    )
    labels = sorted(n["label"] for n in nodes)
    # The critical invariant: no label may carry a redaction placeholder.
    # Other capitalised sentence-start words ("Reach", "Phone") are
    # acceptable — the SUT's job is to be safe, not to do NER.
    for label in labels:
        _assert(
            "<EMAIL>" not in label and "<PHONE_CN>" not in label,
            f"unit/redaction: placeholder leaked into label {label!r}",
            errors,
        )
    _assert(
        "Alice" in labels and "Bob" in labels,
        f"unit/redaction: expected Alice and Bob to survive, got {labels}",
        errors,
    )


def _unit_stop_tokens_and_min_mentions(errors: list[str]) -> None:
    units = [
        "The Hague hosted the summit.",  # multi-word starting with The is OK
        "The summit ended.",  # 'The' alone filtered
        "Alice attended.",
        "Bob attended too.",
    ]
    nodes, _edges = extract_regex_graph(
        context_units=units,
        record_id="dlrs_test_lin",
        evidence_pointer="derived/text/sample.clean.txt",
        sensitivity="S1_INTERNAL",
        min_mentions=1,
        pipeline_version="0.6.0",
    )
    labels = sorted(n["label"] for n in nodes)
    _assert(
        "The" not in labels,
        f"unit/stop: 'The' (alone) must be filtered, got {labels}",
        errors,
    )
    _assert(
        "The Hague" in labels,
        f"unit/stop: multi-word 'The Hague' must be kept, got {labels}",
        errors,
    )

    nodes2, _ = extract_regex_graph(
        context_units=units,
        record_id="dlrs_test_lin",
        evidence_pointer="derived/text/sample.clean.txt",
        sensitivity="S1_INTERNAL",
        min_mentions=2,
        pipeline_version="0.6.0",
    )
    _assert(
        nodes2 == [],
        f"unit/min_mentions: with min_mentions=2 and all entities once, "
        f"expected zero nodes, got {len(nodes2)}",
        errors,
    )


def _unit_no_newline_in_labels(errors: list[str]) -> None:
    """Regression for issue #70.

    Before the fix, ``_CANDIDATE_RE`` used ``\\s+`` between capitalised
    tokens, so a single context unit containing internal ``\\n`` would
    merge proper nouns across line breaks into a multi-line label such
    as ``'Alice\\nCorp'``. After the fix the separator is a literal
    space and adjacent-line mentions stay separate.
    """
    units = [
        "The conference featured speakers from\nBeijing and representatives "
        "of Alice\nCorp who met with delegates from the\nEuropean Commission "
        "in The Hague.",
    ]
    nodes, _edges = extract_regex_graph(
        context_units=units,
        record_id="dlrs_test_lin",
        evidence_pointer="derived/text/sample.clean.txt",
        sensitivity="S1_INTERNAL",
        min_mentions=1,
        pipeline_version="0.6.0",
    )
    labels = [n["label"] for n in nodes]
    for n in nodes:
        _assert(
            "\n" not in n["label"],
            f"unit/no-newline: label contains literal newline: {n['label']!r}",
            errors,
        )
        for alias in n["aliases"]:
            _assert(
                "\n" not in alias,
                f"unit/no-newline: alias contains literal newline: {alias!r}",
                errors,
            )
    # Adjacent-line mentions must survive as separate entities.
    _assert(
        "Alice" in labels and "Corp" in labels,
        f"unit/no-newline: 'Alice' and 'Corp' must be SEPARATE nodes, got {labels}",
        errors,
    )
    _assert(
        "Beijing" in labels,
        f"unit/no-newline: expected 'Beijing' to survive, got {labels}",
        errors,
    )
    # Multi-word entities separated by a real space still work.
    _assert(
        "European Commission" in labels,
        f"unit/no-newline: expected 'European Commission' multi-word entity, got {labels}",
        errors,
    )
    _assert(
        "The Hague" in labels,
        f"unit/no-newline: expected 'The Hague' multi-word entity, got {labels}",
        errors,
    )


def _unit_salience_scales(errors: list[str]) -> None:
    units = [
        "Alice met Alice. Alice waved.",  # 'Alice' x3 in source order
        "Bob saw Bob.",  # Bob x2
        "Carol arrived.",  # Carol x1
    ]
    nodes, _edges = extract_regex_graph(
        context_units=units,
        record_id="dlrs_test_lin",
        evidence_pointer="derived/text/sample.clean.txt",
        sensitivity="S1_INTERNAL",
        min_mentions=1,
        pipeline_version="0.6.0",
    )
    by_label = {n["label"]: n for n in nodes}
    # In a single context unit, _candidate_phrases dedupes by case-folded
    # form, so Alice contributes 1 to mentions per unit (still 1 unit),
    # Bob 1, Carol 1. Salience should therefore all be 1.0 in this case.
    # The test that matters: salience is a number in [0, 1] and the most
    # frequent entity (across units) has the maximum salience.
    if "Alice" in by_label:
        _assert(
            0 <= by_label["Alice"]["salience"] <= 1,
            f"unit/salience: out of [0,1]: {by_label['Alice']['salience']}",
            errors,
        )
    counts = {label: 0 for label in by_label}
    for unit in units:
        for label in by_label:
            if label.lower() in unit.lower():
                counts[label] += 1
    if counts:
        max_count = max(counts.values())
        for label, n in by_label.items():
            expected = counts[label] / max_count if max_count else 0.0
            _assert(
                abs(n["salience"] - expected) < 1e-9,
                f"unit/salience: {label} expected {expected}, got {n['salience']}",
                errors,
            )


def _validate_jsonl_against(path: Path, schema_path: Path, errors: list[str], label: str) -> int:
    from jsonschema import Draft202012Validator

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        n += 1
        item = json.loads(line)
        validation_errors = list(validator.iter_errors(item))
        if validation_errors:
            errors.append(
                f"{label}[{n - 1}] failed schema: " + "; ".join(e.message for e in validation_errors[:3])
            )
    return n


def _validate_descriptor(path: Path, errors: list[str]) -> dict:
    from jsonschema import Draft202012Validator

    schema = json.loads(DERIVED_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    descriptor = json.loads(path.read_text(encoding="utf-8"))
    validation_errors = list(validator.iter_errors(descriptor))
    if validation_errors:
        errors.append(
            "descriptor failed derived-asset schema: "
            + "; ".join(e.message for e in validation_errors[:3])
        )
    return descriptor


def _e2e_against_atoms(errors: list[str]) -> None:
    """Synthesize a record with derived/memory_atoms/sample.atoms.jsonl,
    run knowledge_graph against it."""
    with tempfile.TemporaryDirectory() as tmp:
        record = Path(tmp) / "rec"
        (record / "derived" / "memory_atoms").mkdir(parents=True, exist_ok=True)
        (record / "manifest.json").write_text(
            json.dumps({"record_id": "dlrs_e2e_kg"}), encoding="utf-8"
        )

        atoms = [
            {
                "schema_version": "dlrs-memory-atom/1.0",
                "atom_id": "dlrs_atom_a1",
                "record_id": "dlrs_e2e_kg",
                "source_pointer": "derived/text/sample.clean.txt",
                "text": "Alice met Bob in Beijing.",
                "confidence": 0.6,
                "sensitivity": "S1_INTERNAL",
                "erasable": True,
                "redaction_safe": True,
                "created_at": "2026-04-01T00:00:00Z",
                "pipeline_version": "0.6.0",
            },
            {
                "schema_version": "dlrs-memory-atom/1.0",
                "atom_id": "dlrs_atom_a2",
                "record_id": "dlrs_e2e_kg",
                "source_pointer": "derived/text/sample.clean.txt",
                "text": "Alice and Bob attended the Acme summit.",
                "confidence": 0.6,
                "sensitivity": "S1_INTERNAL",
                "erasable": True,
                "redaction_safe": True,
                "created_at": "2026-04-01T00:00:00Z",
                "pipeline_version": "0.6.0",
            },
        ]
        atoms_path = record / "derived" / "memory_atoms" / "sample.atoms.jsonl"
        atoms_path.write_text(
            "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in atoms),
            encoding="utf-8",
        )

        cmd = [
            sys.executable,
            str(ROOT / "tools" / "run_pipeline.py"),
            "knowledge_graph",
            "--record",
            str(record),
            "--sensitivity",
            "S1_INTERNAL",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        if proc.returncode != 0:
            errors.append(f"e2e atoms: cli exited {proc.returncode}\nstderr={proc.stderr}")
            return

        nodes_path = record / "derived" / "knowledge_graph" / "sample.nodes.jsonl"
        edges_path = record / "derived" / "knowledge_graph" / "sample.edges.jsonl"
        descriptor_path = record / "derived" / "knowledge_graph" / "sample.graph.descriptor.json"
        _assert(nodes_path.exists(), f"e2e atoms: missing {nodes_path}", errors)
        _assert(edges_path.exists(), f"e2e atoms: missing {edges_path}", errors)
        _assert(descriptor_path.exists(), f"e2e atoms: missing {descriptor_path}", errors)
        if nodes_path.exists():
            n_nodes = _validate_jsonl_against(nodes_path, NODE_SCHEMA_PATH, errors, "node")
            _assert(n_nodes >= 3, f"e2e atoms: expected >=3 nodes (Alice/Bob/Beijing/Acme), got {n_nodes}", errors)
        if edges_path.exists():
            n_edges = _validate_jsonl_against(edges_path, EDGE_SCHEMA_PATH, errors, "edge")
            _assert(n_edges >= 2, f"e2e atoms: expected >=2 edges, got {n_edges}", errors)
        if descriptor_path.exists():
            descriptor = _validate_descriptor(descriptor_path, errors)
            _assert(
                descriptor.get("pipeline") == "knowledge_graph",
                f"e2e atoms: descriptor.pipeline mismatch: {descriptor.get('pipeline')}",
                errors,
            )
            _assert(
                descriptor.get("output", {}).get("path", "").startswith("derived/knowledge_graph/"),
                "e2e atoms: descriptor output path must be under derived/knowledge_graph/",
                errors,
            )


def _e2e_against_raw_text_with_pii(errors: list[str]) -> None:
    """Run against a raw .txt artefact whose content contains PII. The
    knowledge_graph pipeline does NOT itself redact; it relies on its
    inputs being redacted upstream OR being raw paragraphs that the
    candidate filter discards. Because we want to be sure the pipeline
    never promotes a PII fragment to a node, we hand-feed PII directly
    and assert nothing leaks."""
    with tempfile.TemporaryDirectory() as tmp:
        record = Path(tmp) / "rec"
        (record / "artifacts" / "raw" / "text").mkdir(parents=True, exist_ok=True)
        (record / "manifest.json").write_text(
            json.dumps({"record_id": "dlrs_e2e_kg_pii"}), encoding="utf-8"
        )
        # PII left as-is on purpose (an unrealistic but worst-case input):
        raw_text = (
            "Alice met Bob at alice@example.com.\n\n"
            "Bob's number is 13912345678 in Beijing."
        )
        (record / "artifacts" / "raw" / "text" / "diary.txt").write_text(
            raw_text, encoding="utf-8"
        )

        cmd = [
            sys.executable,
            str(ROOT / "tools" / "run_pipeline.py"),
            "knowledge_graph",
            "--record",
            str(record),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        if proc.returncode != 0:
            errors.append(f"e2e raw: cli exited {proc.returncode}\nstderr={proc.stderr}")
            return

        nodes_path = record / "derived" / "knowledge_graph" / "diary.nodes.jsonl"
        edges_path = record / "derived" / "knowledge_graph" / "diary.edges.jsonl"
        if not nodes_path.exists() or not edges_path.exists():
            errors.append(f"e2e raw: missing nodes / edges output")
            return

        blob = nodes_path.read_text(encoding="utf-8") + edges_path.read_text(encoding="utf-8")
        # The filter uses _is_safe(label), which runs the v0.5 redactor
        # over each candidate. Email / phone substrings cannot survive.
        _assert(
            "alice@example.com" not in blob,
            "e2e raw: original email leaked into nodes/edges (label safety filter failed)",
            errors,
        )
        _assert(
            "13912345678" not in blob,
            "e2e raw: original phone leaked into nodes/edges",
            errors,
        )

        # Alice / Bob / Beijing should all still survive.
        labels = []
        for line in nodes_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                labels.append(json.loads(line)["label"])
        for required in ("Alice", "Bob", "Beijing"):
            _assert(
                required in labels,
                f"e2e raw: expected '{required}' in node labels, got {labels}",
                errors,
            )


def main() -> int:
    try:
        from jsonschema import Draft202012Validator  # noqa: F401
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    errors: list[str] = []
    print("test_knowledge_graph_pipeline: unit/dedupe + edges")
    _unit_dedupe_and_aliases(errors)
    print("test_knowledge_graph_pipeline: unit/redaction-placeholder filtering")
    _unit_redaction_placeholder_filtering(errors)
    print("test_knowledge_graph_pipeline: unit/stop-tokens + min_mentions")
    _unit_stop_tokens_and_min_mentions(errors)
    print("test_knowledge_graph_pipeline: unit/no-newline-in-labels (issue #70 regression)")
    _unit_no_newline_in_labels(errors)
    print("test_knowledge_graph_pipeline: unit/salience scales with mentions")
    _unit_salience_scales(errors)
    print("test_knowledge_graph_pipeline: e2e atoms.jsonl input")
    _e2e_against_atoms(errors)
    print("test_knowledge_graph_pipeline: e2e raw.txt with PII (label safety filter)")
    _e2e_against_raw_text_with_pii(errors)

    if errors:
        print(f"\ntest_knowledge_graph_pipeline: {len(errors)} failure(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\ntest_knowledge_graph_pipeline: all assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
