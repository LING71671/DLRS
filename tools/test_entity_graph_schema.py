#!/usr/bin/env python3
"""Sanity tests for ``schemas/entity-graph-node.schema.json`` and
``schemas/entity-graph-edge.schema.json``.

Mirrors the structure of ``test_memory_atom_schema.py`` and
``test_derived_asset_schema.py``: construct known-good documents, then
mutate each to provoke schema-level rejections. The pipelines/knowledge_graph/
implementation (issue #57) will reuse these schemas to validate every node /
edge it emits.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_SCHEMA_PATH = ROOT / "schemas" / "entity-graph-node.schema.json"
EDGE_SCHEMA_PATH = ROOT / "schemas" / "entity-graph-edge.schema.json"


def _good_node() -> dict:
    return {
        "schema_version": "dlrs-entity-graph-node/1.0",
        "node_id": "01HW91QJTR4ETRBM3DNJK4Y9MA",
        "record_id": "dlrs_94f1c9b8_lin-example",
        "kind": "person",
        "label": "林某",
        "aliases": ["Lin Mou", "Lin"],
        "salience": 0.8,
        "sensitivity": "S1_INTERNAL",
        "redaction_safe": True,
        "created_at": "2026-04-26T08:00:00Z",
        "pipeline_version": "0.6.0",
    }


def _good_edge() -> dict:
    return {
        "schema_version": "dlrs-entity-graph-edge/1.0",
        "edge_id": "dlrs_edge_4f3e2a8c",
        "record_id": "dlrs_94f1c9b8_lin-example",
        "subject_node_id": "01HW91QJTR4ETRBM3DNJK4Y9MA",
        "object_node_id": "dlrs_node_acme01",
        "relation": "dlrs.member_of",
        "evidence_pointer": "derived/text/diary_2026-04-01.clean.txt",
        "confidence": 0.7,
        "sensitivity": "S1_INTERNAL",
        "redaction_safe": True,
        "created_at": "2026-04-26T08:00:00Z",
        "pipeline_version": "0.6.0",
    }


def _run_cases(label: str, schema_path: Path, cases: list[tuple[str, dict, bool]]) -> int:
    from jsonschema import Draft202012Validator

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    failures = 0
    for name, doc, expect_valid in cases:
        errors = list(validator.iter_errors(doc))
        is_valid = not errors
        if is_valid != expect_valid:
            failures += 1
            print(f"FAIL  [{label}] {name}: expected valid={expect_valid} got valid={is_valid}")
            for e in errors[:3]:
                print(f"      - {e.message}")
        else:
            print(f"OK    [{label}] {name}")
    return failures


def main() -> int:
    try:
        from jsonschema import Draft202012Validator  # noqa: F401  (imported in helper)
    except ImportError:
        print("ERROR: jsonschema not installed; run: pip install -r tools/requirements.txt")
        return 2

    # --- node cases ---
    node_cases: list[tuple[str, dict, bool]] = []
    node_cases.append(("good node", _good_node(), True))

    # empty aliases is allowed
    no_aliases = _good_node()
    no_aliases["aliases"] = []
    node_cases.append(("empty aliases", no_aliases, True))

    # full optional set
    full = _good_node()
    full["audit_event_ref"] = "audit/events.jsonl#L142"
    node_cases.append(("good node with audit_event_ref", full, True))

    # redaction_safe=false -> reject
    not_safe = _good_node()
    not_safe["redaction_safe"] = False
    node_cases.append(("redaction_safe=false", not_safe, False))

    # missing redaction_safe -> reject
    missing_safe = _good_node()
    missing_safe.pop("redaction_safe")
    node_cases.append(("missing redaction_safe", missing_safe, False))

    # kind outside enum -> reject
    bad_kind = _good_node()
    bad_kind["kind"] = "deity"
    node_cases.append(("kind outside enum", bad_kind, False))

    # salience > 1 -> reject
    over_sal = _good_node()
    over_sal["salience"] = 1.5
    node_cases.append(("salience > 1", over_sal, False))

    # label empty -> reject
    empty_label = _good_node()
    empty_label["label"] = ""
    node_cases.append(("empty label", empty_label, False))

    # aliases > 64 -> reject
    too_many_aliases = _good_node()
    too_many_aliases["aliases"] = ["a" + str(i) for i in range(65)]
    node_cases.append(("aliases > 64", too_many_aliases, False))

    # additionalProperties -> reject
    extra = _good_node()
    extra["random_extra"] = 1
    node_cases.append(("unknown top-level field", extra, False))

    # wrong schema_version -> reject
    wrong_v = _good_node()
    wrong_v["schema_version"] = "dlrs-entity-graph-node/1.1"
    node_cases.append(("wrong schema_version", wrong_v, False))

    # node_id pattern violation -> reject (too short)
    short_id = _good_node()
    short_id["node_id"] = "abc"
    node_cases.append(("node_id too short", short_id, False))

    # --- edge cases ---
    edge_cases: list[tuple[str, dict, bool]] = []
    edge_cases.append(("good edge", _good_edge(), True))

    full_edge = _good_edge()
    full_edge["audit_event_ref"] = "audit/events.jsonl#L143"
    edge_cases.append(("good edge with audit_event_ref", full_edge, True))

    # redaction_safe=false -> reject
    edge_not_safe = _good_edge()
    edge_not_safe["redaction_safe"] = False
    edge_cases.append(("edge redaction_safe=false", edge_not_safe, False))

    # missing relation -> reject
    no_rel = _good_edge()
    no_rel.pop("relation")
    edge_cases.append(("missing relation", no_rel, False))

    # subject_node_id pattern violation -> reject
    bad_subj = _good_edge()
    bad_subj["subject_node_id"] = "short"
    edge_cases.append(("subject_node_id too short", bad_subj, False))

    # object_node_id missing -> reject
    no_obj = _good_edge()
    no_obj.pop("object_node_id")
    edge_cases.append(("missing object_node_id", no_obj, False))

    # absolute evidence_pointer -> reject
    abs_evidence = _good_edge()
    abs_evidence["evidence_pointer"] = "/tmp/diary.txt"
    edge_cases.append(("absolute evidence_pointer", abs_evidence, False))

    # https evidence_pointer -> reject
    url_evidence = _good_edge()
    url_evidence["evidence_pointer"] = "https://example.org/diary.txt"
    edge_cases.append(("https evidence_pointer", url_evidence, False))

    # confidence > 1 -> reject
    over_conf = _good_edge()
    over_conf["confidence"] = 1.2
    edge_cases.append(("edge confidence > 1", over_conf, False))

    # additionalProperties -> reject
    edge_extra = _good_edge()
    edge_extra["random_extra"] = 1
    edge_cases.append(("edge unknown top-level field", edge_extra, False))

    failures = _run_cases("node", NODE_SCHEMA_PATH, node_cases)
    failures += _run_cases("edge", EDGE_SCHEMA_PATH, edge_cases)

    total = len(node_cases) + len(edge_cases)
    if failures:
        print(f"\ntest_entity_graph_schema: {failures}/{total} case(s) failed")
        return 1
    print(f"\ntest_entity_graph_schema: all {total} case(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
