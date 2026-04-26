"""Deterministic regex-based knowledge-graph extraction.

The default v0.6 backend deliberately stays simple and dependency-free so
the pipeline runs identically on a laptop and in CI:

- Entity candidates are runs of capitalised tokens (``[A-Z][a-z]+``,
  optionally separated by single spaces). Single-token candidates are
  accepted only if they are not in the small ``_STOP_TOKENS`` set
  (sentence-start words, pronouns, common articles).
- Candidates that contain a v0.5 redaction placeholder (``<EMAIL>``,
  ``<PHONE_CN>``, …) are dropped, since those placeholders are not
  meaningful entities.
- Candidates that match a v0.5 redaction pattern (e.g. a literal email
  somehow leaked into the input) are also dropped, so an entity label
  cannot itself be a leak vector.
- Within each context unit (one atom, or one paragraph of cleaned text),
  consecutive deduplicated mentions become a ``dlrs.co_mentioned_in``
  edge with ``confidence = 0.5``. We use **consecutive** rather than
  fully connected pairs so a long context with N mentions emits N-1
  edges, not N(N-1)/2 — proportional to discourse, not to cardinality.
- Salience is the per-entity mention count divided by the maximum
  mention count, clamped to ``[0, 1]``.

A node's ``aliases`` list collects every surface form (case-sensitive)
under which the entity was seen, deduplicated and capped at the schema
maximum (64 items).
"""
from __future__ import annotations

import datetime as _dt
import re
import uuid
from typing import Iterable, List, Tuple


_NODE_KIND = "other"
_EDGE_RELATION = "dlrs.co_mentioned_in"
_EDGE_CONFIDENCE = 0.5
_ALIAS_CAP = 64

# Conservative capitalised-token-run pattern. Matches up to 4 tokens so a
# whole sentence of capitalised words doesn't collapse into a single
# absurd "entity". The inter-token separator is a *literal space* — not
# ``\s+`` — so capitalised words on adjacent lines (line-wrapped prose)
# do NOT merge into a single multi-line entity with a literal ``\n``
# embedded in its label. See issue #70 for the regression repro.
_CANDIDATE_RE = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+){0,3})\b")

# Tokens that, when they appear as a single-word candidate, are almost
# never proper nouns. Multi-word phrases starting with one of these (e.g.
# "The Hague") are kept; only standalone single-token mentions are
# filtered.
_STOP_TOKENS = frozenset({
    "A", "An", "And", "As", "At", "But", "By",
    "For", "From", "He", "Her", "His", "I", "In", "Is", "It", "Its",
    "My", "No", "Of", "On", "Or", "She", "So", "That", "The", "Their",
    "Then", "There", "These", "They", "This", "Those", "To", "Was",
    "We", "Were", "What", "When", "Where", "Which", "Who", "Why",
    "With", "You", "Your",
})

# Anything that the v0.5 redactor would replace. Used to drop candidates
# whose surface form is itself a leak.
_FORBIDDEN_IN_LABEL = re.compile(
    r"<(?:EMAIL|PHONE_CN|PHONE|ID_CN|IPV4|CARD|URL_WITH_CREDENTIALS)>"
)


def _utc_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _node_id() -> str:
    return f"dlrs_node_{uuid.uuid4().hex[:12]}"


def _edge_id() -> str:
    return f"dlrs_edge_{uuid.uuid4().hex[:12]}"


def _is_safe(label: str) -> bool:
    """Reject labels that contain redaction placeholders or match the v0.5
    redaction patterns. The latter case is unusual (the input should have
    been redacted already) but we belt-and-brace anyway."""
    if _FORBIDDEN_IN_LABEL.search(label):
        return False
    # Lazy import: avoid loading the regex bank when this branch is cold.
    from pipelines.text.cleaning import redact

    _, redactions = redact(label)
    return not redactions


def _candidate_phrases(unit: str) -> List[str]:
    """Yield deduped capitalised phrases from a context unit, in source order."""
    seen: set[str] = set()
    out: List[str] = []
    for match in _CANDIDATE_RE.finditer(unit):
        phrase = match.group(1).strip()
        if not phrase:
            continue
        if " " not in phrase and phrase in _STOP_TOKENS:
            continue
        if not _is_safe(phrase):
            continue
        # Within a single unit, dedupe by case-folded form so the same
        # entity mentioned twice in the same paragraph is reported once
        # for edge construction.
        key = phrase.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(phrase)
    return out


def extract_regex_graph(
    context_units: Iterable[str],
    record_id: str,
    evidence_pointer: str,
    sensitivity: str,
    min_mentions: int,
    pipeline_version: str,
) -> Tuple[List[dict], List[dict]]:
    """Extract nodes + ``dlrs.co_mentioned_in`` edges from context units.

    Args:
        context_units: Iterable of strings; one entry per atom or
            paragraph. Edges are only emitted within a single unit.
        record_id: Owning DLRS record id; copied onto every emitted node
            and edge.
        evidence_pointer: Path (relative to the record root) of the
            input artefact; copied to every edge's ``evidence_pointer``.
        sensitivity: One of the S0..S4 enum values; copied onto every
            node and edge.
        min_mentions: Drop entities seen strictly fewer than this many
            times across all units. ``1`` keeps everything.
        pipeline_version: SemVer-ish string; the v0.6 pipeline pins this
            to the module-level ``PIPELINE_VERSION``.

    Returns:
        ``(nodes, edges)`` — two lists of dicts, each conforming to its
        respective entity-graph schema.
    """
    # Pass 1: tally mentions and collect aliases per case-folded label.
    mentions: dict[str, list[str]] = {}
    per_unit_phrases: list[list[str]] = []
    for unit in context_units:
        phrases = _candidate_phrases(unit)
        per_unit_phrases.append(phrases)
        for phrase in phrases:
            mentions.setdefault(phrase.lower(), []).append(phrase)

    # Apply the min_mentions threshold.
    kept: dict[str, list[str]] = {
        k: v for k, v in mentions.items() if len(v) >= max(1, min_mentions)
    }
    if not kept:
        return [], []

    max_count = max(len(v) for v in kept.values())

    # Build nodes deterministically: sorted by descending mention count,
    # then alphabetically by canonical label, so the file is stable and
    # easy to diff. node_id itself is uuid-derived (non-deterministic by
    # design — see schema docs) so re-runs do not collide.
    nodes_by_key: dict[str, dict] = {}
    label_for_key: dict[str, str] = {}
    for key in sorted(kept, key=lambda k: (-len(kept[k]), k)):
        # Canonical label: most-frequent surface form, ties broken by
        # source-order first occurrence (which is what list[0] gives us
        # because mentions are appended in source order).
        surfaces = kept[key]
        # most-common surface form
        counts: dict[str, int] = {}
        for s in surfaces:
            counts[s] = counts.get(s, 0) + 1
        canonical = max(counts.items(), key=lambda kv: (kv[1], -surfaces.index(kv[0])))[0]
        aliases = []
        seen_alias: set[str] = set()
        for s in surfaces:
            if s == canonical or s in seen_alias:
                continue
            seen_alias.add(s)
            aliases.append(s)
            if len(aliases) >= _ALIAS_CAP:
                break
        salience = len(surfaces) / max_count if max_count else 0.0
        node = {
            "schema_version": "dlrs-entity-graph-node/1.0",
            "node_id": _node_id(),
            "record_id": record_id,
            "kind": _NODE_KIND,
            "label": canonical,
            "aliases": aliases,
            "salience": salience,
            "sensitivity": sensitivity,
            "redaction_safe": True,
            "created_at": _utc_now(),
            "pipeline_version": pipeline_version,
        }
        nodes_by_key[key] = node
        label_for_key[key] = canonical

    nodes = list(nodes_by_key.values())

    # Pass 2: build co-mention edges between consecutive surviving
    # mentions inside each unit. Skip self-loops, dedupe within a unit so
    # repeated alternations don't produce N-1 identical edges.
    edges: list[dict] = []
    for phrases in per_unit_phrases:
        # Filter to surviving keys, in source order.
        surviving = [p for p in phrases if p.lower() in nodes_by_key]
        # Dedupe consecutive duplicates from the same key.
        deduped: list[str] = []
        for p in surviving:
            if deduped and p.lower() == deduped[-1].lower():
                continue
            deduped.append(p)
        seen_pairs: set[tuple[str, str]] = set()
        for a, b in zip(deduped, deduped[1:]):
            ka, kb = a.lower(), b.lower()
            if ka == kb:
                continue
            pair = (ka, kb)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            edges.append(
                {
                    "schema_version": "dlrs-entity-graph-edge/1.0",
                    "edge_id": _edge_id(),
                    "record_id": record_id,
                    "subject_node_id": nodes_by_key[ka]["node_id"],
                    "object_node_id": nodes_by_key[kb]["node_id"],
                    "relation": _EDGE_RELATION,
                    "evidence_pointer": evidence_pointer,
                    "confidence": _EDGE_CONFIDENCE,
                    "sensitivity": sensitivity,
                    "redaction_safe": True,
                    "created_at": _utc_now(),
                    "pipeline_version": pipeline_version,
                }
            )
    return nodes, edges
