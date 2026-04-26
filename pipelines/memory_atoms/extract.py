"""Memory-atom extraction backends.

Two backends are supported:

- :func:`extract_paragraph_atoms` (default): deterministic, dependency-free.
  Splits on blank lines and emits one atom per non-empty paragraph.
- :func:`extract_spacy_atoms` (opt-in): lazy-imports spaCy and runs its
  language-agnostic sentencizer. Each sentence becomes one atom.

Both backends:

- Produce atoms that conform to ``schemas/memory-atom.schema.json``.
- Stamp ``redaction_safe = True`` (the contract; the caller has already
  ensured the text passed through the v0.5 redactor).
- Generate stable but unique ``atom_id`` per emission via :mod:`uuid` so
  re-running the pipeline on byte-identical inputs still produces fresh
  atom IDs (per the schema's immutability documentation).
- Pin ``confidence`` to a backend-specific baseline:

  - paragraph: ``0.6`` (deterministic baseline; tooling can use the
    ``model`` block's absence to detect this backend).
  - spacy: ``0.7`` (the sentencizer is more granular but still rule-based;
    bump to a model-derived score once a real NER backend lands).
"""
from __future__ import annotations

import datetime as _dt
import re
import uuid
from typing import List


_ATOM_TEXT_CAP = 4096
_PARAGRAPH_CONFIDENCE = 0.6
_SPACY_CONFIDENCE = 0.7

# Paragraph splitter: one or more blank lines (allowing trailing whitespace
# on the blank lines, which ``pipelines.text.cleaning.normalise`` would
# already have stripped, but be defensive in case the pipeline runs against
# raw text).
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")


def _utc_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atom_id() -> str:
    return f"dlrs_atom_{uuid.uuid4().hex[:12]}"


def _truncate(text: str) -> str:
    if len(text) <= _ATOM_TEXT_CAP:
        return text
    # Keep the first cap characters; longer extractions should be chunked
    # into multiple atoms by the backend before this guard fires. The guard
    # exists so that a misbehaving custom backend cannot violate the schema.
    return text[:_ATOM_TEXT_CAP]


def _build_atom(
    text: str,
    record_id: str,
    source_pointer: str,
    sensitivity: str,
    erasable: bool,
    confidence: float,
    pipeline_version: str,
) -> dict:
    return {
        "schema_version": "dlrs-memory-atom/1.0",
        "atom_id": _atom_id(),
        "record_id": record_id,
        "source_pointer": source_pointer,
        "text": _truncate(text),
        "confidence": confidence,
        "sensitivity": sensitivity,
        "erasable": erasable,
        "redaction_safe": True,
        "created_at": _utc_now(),
        "pipeline_version": pipeline_version,
    }


def extract_paragraph_atoms(
    text: str,
    record_id: str,
    source_pointer: str,
    sensitivity: str,
    erasable: bool,
    pipeline_version: str,
) -> List[dict]:
    """Split ``text`` on blank lines and emit one atom per non-empty paragraph."""
    atoms: List[dict] = []
    for chunk in _PARAGRAPH_SPLIT.split(text):
        chunk = chunk.strip()
        if not chunk:
            continue
        atoms.append(
            _build_atom(
                text=chunk,
                record_id=record_id,
                source_pointer=source_pointer,
                sensitivity=sensitivity,
                erasable=erasable,
                confidence=_PARAGRAPH_CONFIDENCE,
                pipeline_version=pipeline_version,
            )
        )
    return atoms


def extract_spacy_atoms(
    text: str,
    record_id: str,
    source_pointer: str,
    sensitivity: str,
    erasable: bool,
    pipeline_version: str,
) -> List[dict]:
    """Run spaCy's sentencizer over ``text``; one atom per sentence.

    spaCy is imported lazily so the rest of the pipeline (including the
    paragraph backend) never pulls it in.
    """
    try:
        import spacy  # type: ignore
    except ImportError as exc:  # pragma: no cover - opt-in dependency
        raise SystemExit(
            "[memory_atoms] backend=spacy requires spaCy; install with "
            "'pip install spacy' (no model download required for the "
            "language-agnostic sentencizer)"
        ) from exc

    nlp = spacy.blank("xx")
    if "sentencizer" not in nlp.pipe_names:  # pragma: no branch
        nlp.add_pipe("sentencizer")

    atoms: List[dict] = []
    doc = nlp(text)
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if not sent_text:
            continue
        atoms.append(
            _build_atom(
                text=sent_text,
                record_id=record_id,
                source_pointer=source_pointer,
                sensitivity=sensitivity,
                erasable=erasable,
                confidence=_SPACY_CONFIDENCE,
                pipeline_version=pipeline_version,
            )
        )
    return atoms
