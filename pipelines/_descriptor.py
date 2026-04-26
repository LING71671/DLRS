"""Shared helpers for emitting derived-asset descriptors.

Every concrete pipeline (``pipelines.asr``, ``pipelines.text``,
``pipelines.vectorization``, ``pipelines.moderation``) writes its primary
artefact under ``<record>/derived/<pipeline>/...`` and a sibling descriptor
that conforms to ``schemas/derived-asset.schema.json``.

Centralising the descriptor emitter here means:

- Hash discipline (sha256, hex, lowercase) is consistent across pipelines.
- Schema validation lives in one place; if a pipeline ever drifts away
  from the contract, it fails the same way.
- New pipelines (or refactors of existing ones) only have to fill in the
  pipeline-specific bits, not re-implement provenance plumbing.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Schema version pinned to the const declared in
# ``schemas/derived-asset.schema.json``. Bump both in lock-step.
DERIVED_SCHEMA_VERSION = "dlrs-derived-asset/1.0"


def _utc_now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            h.update(buf)
    return "sha256:" + h.hexdigest()


def sha256_of_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def combine_input_hashes(per_file_hashes: List[str]) -> str:
    """Stable hash of an ordered list of input file hashes.

    The descriptor's ``inputs.inputs_hash`` is the sha256 of the
    canonical ``\\n``-joined hex digests of the inputs, in declared order.
    Using a deterministic concatenation avoids serialisation ambiguity on
    different platforms.
    """
    if not per_file_hashes:
        raise ValueError("at least one input hash is required")
    blob = "\n".join(per_file_hashes).encode("utf-8")
    return sha256_of_bytes(blob)


@dataclass
class ModelInfo:
    """Optional model identification block inside a descriptor."""

    id: str
    version: Optional[str] = None
    source: Optional[str] = None
    online_api_used: bool = False  # MUST stay False under the v0.5 invariant

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id, "online_api_used": self.online_api_used}
        if self.version is not None:
            d["version"] = self.version
        if self.source is not None:
            d["source"] = self.source
        return d


@dataclass
class DescriptorBuilder:
    """Mutable builder for a derived-asset descriptor.

    Pipelines populate it incrementally as they run and call
    :meth:`finalise` after the output file has been written.
    """

    record_id: str
    pipeline: str
    pipeline_version: str
    actor_role: str = "system"
    derived_id: str = field(default_factory=lambda: f"dlrs_derived_{uuid.uuid4().hex[:12]}")
    parameters: Dict[str, Any] = field(default_factory=dict)
    preprocessing: Dict[str, Any] = field(default_factory=dict)
    source_pointers: List[str] = field(default_factory=list)
    input_file_hashes: List[str] = field(default_factory=list)
    model: Optional[ModelInfo] = None
    audit_event_ref: Optional[str] = None
    moderation_outcome: Optional[str] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def add_input(self, source_pointer: str, file_path: Path) -> None:
        """Record one input file (path-relative-to-record + its hash)."""
        self.source_pointers.append(source_pointer)
        self.input_file_hashes.append(sha256_of_file(file_path))

    def finalise(self, output_path_in_record: str, output_file: Path) -> Dict[str, Any]:
        """Build the descriptor dict.

        Args:
            output_path_in_record: Path of the produced artefact relative to
                the record root, e.g. ``"derived/asr/voice.transcript.json"``.
                MUST start with ``derived/<pipeline>/``.
            output_file: Filesystem path to the produced file (used for the
                output hash and ``byte_size`` field).
        """
        if not output_path_in_record.startswith(f"derived/{self.pipeline}/"):
            raise ValueError(
                f"output path {output_path_in_record!r} must start with "
                f"derived/{self.pipeline}/"
            )
        if not self.input_file_hashes:
            raise ValueError("no inputs recorded; call add_input() at least once")

        descriptor: Dict[str, Any] = {
            "schema_version": DERIVED_SCHEMA_VERSION,
            "derived_id": self.derived_id,
            "record_id": self.record_id,
            "pipeline": self.pipeline,
            "pipeline_version": self.pipeline_version,
            "created_at": _utc_now(),
            "actor_role": self.actor_role,
            "inputs": {
                "source_pointers": list(self.source_pointers),
                "inputs_hash": combine_input_hashes(self.input_file_hashes),
            },
            "parameters": dict(self.parameters),
            "output": {
                "path": output_path_in_record,
                "outputs_hash": sha256_of_file(output_file),
                "byte_size": output_file.stat().st_size,
            },
        }
        if self.preprocessing:
            descriptor["inputs"]["preprocessing"] = dict(self.preprocessing)
        if self.model is not None:
            descriptor["model"] = self.model.to_dict()
        if self.audit_event_ref is not None:
            descriptor["audit_event_ref"] = self.audit_event_ref
        if self.moderation_outcome is not None:
            descriptor["moderation_outcome"] = self.moderation_outcome
        if self.extra_metadata:
            descriptor["metadata"] = dict(self.extra_metadata)
        return descriptor


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Atomically write ``payload`` to ``path`` as canonical JSON.

    Uses ``os.replace`` so that a partially-written file is never visible
    to readers — important because the descriptor's ``outputs_hash`` is
    computed off the on-disk artefact.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def validate_descriptor(descriptor: Dict[str, Any], schema_path: Path) -> None:
    """Validate a descriptor against ``schemas/derived-asset.schema.json``.

    Raises ``ValueError`` (with the consolidated jsonschema error list) if
    validation fails so pipelines abort cleanly without leaving a stray
    descriptor next to a real artefact.
    """
    from jsonschema import Draft202012Validator  # type: ignore

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(descriptor), key=lambda e: e.path)
    if errors:
        msg = "; ".join(f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors)
        raise ValueError(f"derived-asset descriptor failed schema validation: {msg}")
