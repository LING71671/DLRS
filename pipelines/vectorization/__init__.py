"""Embedding + Qdrant indexing pipeline.

Inputs:

- ``derived/text/<stem>.clean.txt`` produced by :mod:`pipelines.text`.
- Any plain text file via ``--input``.

Outputs (under ``<record>/derived/vectorization/``):

- ``<stem>.index.json`` — the on-disk vector index. Contains every
  chunk's text-excerpt sha256, character span, and the embedding vector
  itself. With the ``hash`` backend the file is small (~64 floats per
  chunk); with ``sentence-transformers`` it's larger but still readable.
- ``<stem>.index.descriptor.json`` — provenance descriptor conforming to
  ``schemas/derived-asset.schema.json``.

Optional Qdrant push:

  ``--qdrant-url http://127.0.0.1:6333`` will write the same vectors
  into a local Qdrant collection. Disabled by default so CI stays
  network-free; the index.json is the source of truth either way.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipelines import PipelineSpec
from pipelines._descriptor import (
    DescriptorBuilder,
    ModelInfo,
    validate_descriptor,
    write_json,
)
from pipelines._audit_bridge import maybe_bridge

PIPELINE_VERSION = "0.5.0"

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "derived-asset.schema.json"


def _register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--record", required=False, help="Path to the record directory.")
    parser.add_argument(
        "--input",
        required=False,
        help="Path to a clean text file. Record-relative when --record is set.",
    )
    parser.add_argument(
        "--backend",
        choices=["hash", "sentence-transformers"],
        default="sentence-transformers",
        help="Embedding backend. 'hash' is deterministic and dependency-free "
             "(used by tests / offline demos); 'sentence-transformers' is the "
             "real backend, lazy-imported.",
    )
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model id (sentence-transformers backend only). "
             "Default: all-MiniLM-L6-v2.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Compute device for sentence-transformers. Default: cpu.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=600,
        help="Soft maximum characters per chunk before sliding. Default: 600.",
    )
    parser.add_argument(
        "--overlap-chars",
        type=int,
        default=80,
        help="Overlap between adjacent windows when a paragraph exceeds "
             "--max-chars. Default: 80.",
    )
    parser.add_argument(
        "--qdrant-url",
        default=None,
        help="Optional local Qdrant URL (e.g. http://127.0.0.1:6333). When "
             "omitted, the index.json is the only output.",
    )
    parser.add_argument(
        "--collection",
        default=None,
        help="Qdrant collection name. Defaults to the record id from manifest.json.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory. Default: <record>/derived/vectorization/.",
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip the descriptor->audit/events.jsonl bridge (#58).",
    )


def _resolve_input(args: argparse.Namespace) -> tuple[Optional[Path], Path, str]:
    record_root: Optional[Path] = Path(args.record).resolve() if args.record else None

    if args.input:
        candidate = Path(args.input)
        if record_root is not None and not candidate.is_absolute():
            input_path = (record_root / args.input).resolve()
        else:
            input_path = candidate.resolve()
    else:
        if record_root is None:
            raise SystemExit("[vectorization] one of --input or --record is required")
        input_path = _first_text_in_record(record_root)

    if not input_path.exists():
        raise SystemExit(f"[vectorization] input not found: {input_path}")

    if record_root is not None:
        try:
            pointer_rel = str(input_path.relative_to(record_root))
        except ValueError:
            pointer_rel = input_path.name
    else:
        pointer_rel = input_path.name
    return record_root, input_path, pointer_rel


def _first_text_in_record(record_root: Path) -> Path:
    derived_text = record_root / "derived" / "text"
    if derived_text.is_dir():
        candidates = sorted(derived_text.glob("*.clean.txt"))
        if candidates:
            return candidates[0]
    raise SystemExit(
        f"[vectorization] no derived/text/*.clean.txt found under {record_root}; "
        "run pipelines.text first or pass --input"
    )


def _read_record_id(record_root: Optional[Path], default: str) -> str:
    if record_root is None:
        return default
    manifest = record_root / "manifest.json"
    if not manifest.exists():
        return default
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return data.get("record_id", default)
    except (OSError, json.JSONDecodeError):
        return default


def _stem_for(input_path: Path) -> str:
    name = input_path.name
    for suffix in (".clean.txt",):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return input_path.stem


def _push_to_qdrant(
    *,
    url: str,
    collection: str,
    record_id: str,
    pointer_rel: str,
    backend: str,
    model_id: str,
    result,
) -> dict:
    """Push the vectors to a local Qdrant. Lazy-imported."""
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.http import models as rest  # type: ignore

    client = QdrantClient(url=url)
    client.recreate_collection(
        collection_name=collection,
        vectors_config=rest.VectorParams(size=result.dim, distance=rest.Distance.COSINE),
    )
    points = []
    for chunk, vec in zip(result.chunks, result.vectors):
        points.append(
            rest.PointStruct(
                id=chunk.chunk_id,
                vector=vec,
                payload={
                    "record_id": record_id,
                    "source_pointer": pointer_rel,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "text_sha256": chunk.text_sha256(),
                    "backend": backend,
                    "model_id": model_id,
                },
            )
        )
    client.upsert(collection_name=collection, points=points)
    return {"url": url, "collection": collection, "points": len(points)}


def _run(args: argparse.Namespace) -> int:
    from pipelines.vectorization.embed import chunk_text, embed

    record_root, input_path, pointer_rel = _resolve_input(args)

    if args.output_dir:
        out_dir = Path(args.output_dir).resolve()
    elif record_root is not None:
        out_dir = record_root / "derived" / "vectorization"
    else:
        out_dir = input_path.parent / "derived" / "vectorization"
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = _stem_for(input_path)
    index_path = out_dir / f"{stem}.index.json"
    descriptor_path = out_dir / f"{stem}.index.descriptor.json"

    text = input_path.read_text(encoding="utf-8")
    chunks = chunk_text(text, max_chars=args.max_chars, overlap_chars=args.overlap_chars)
    if not chunks:
        raise SystemExit(f"[vectorization] {input_path} produced no chunks (empty input?)")

    print(
        f"[vectorization] backend={args.backend} chunks={len(chunks)} "
        f"max_chars={args.max_chars} overlap={args.overlap_chars}",
        file=sys.stderr,
    )

    result = embed(
        chunks,
        backend=args.backend,
        model=args.model if args.backend == "sentence-transformers" else None,
        device=args.device,
    )

    index_entries: List[Dict[str, Any]] = []
    for chunk, vec in zip(result.chunks, result.vectors):
        index_entries.append(
            {
                "chunk_id": chunk.chunk_id,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "text_sha256": chunk.text_sha256(),
                "vector": vec,
            }
        )

    qdrant_info: Optional[dict] = None
    record_id = _read_record_id(record_root, default="dlrs_unknown")
    if args.qdrant_url:
        collection = args.collection or record_id
        qdrant_info = _push_to_qdrant(
            url=args.qdrant_url,
            collection=collection,
            record_id=record_id,
            pointer_rel=pointer_rel,
            backend=result.backend,
            model_id=result.model_id,
            result=result,
        )

    write_json(
        index_path,
        {
            "schema": "dlrs-vector-index/1.0",
            "backend": result.backend,
            "model_id": result.model_id,
            "dim": result.dim,
            "chunker_version": "1.0",
            "chunk_count": len(index_entries),
            "qdrant": qdrant_info,
            "entries": index_entries,
        },
    )

    builder = DescriptorBuilder(
        record_id=record_id,
        pipeline="vectorization",
        pipeline_version=PIPELINE_VERSION,
        parameters={
            "backend": args.backend,
            "max_chars": args.max_chars,
            "overlap_chars": args.overlap_chars,
            "device": args.device,
            "qdrant_url": args.qdrant_url,
            "collection": args.collection,
        },
        model=ModelInfo(
            id=result.model_id,
            version=None,
            source="local-cache" if args.backend == "sentence-transformers" else "deterministic",
            online_api_used=False,
        ),
    )
    builder.add_input(source_pointer=pointer_rel, file_path=input_path)
    builder.extra_metadata["chunk_count"] = len(index_entries)
    builder.extra_metadata["dim"] = result.dim
    if qdrant_info is not None:
        builder.extra_metadata["qdrant"] = qdrant_info

    if record_root is not None:
        try:
            out_path_in_record = str(index_path.relative_to(record_root))
        except ValueError:
            out_path_in_record = f"derived/vectorization/{index_path.name}"
    else:
        out_path_in_record = f"derived/vectorization/{index_path.name}"

    descriptor = builder.finalise(out_path_in_record, index_path)
    validate_descriptor(descriptor, SCHEMA_PATH)
    write_json(descriptor_path, descriptor)

    audit_ref = maybe_bridge(
        record_root=record_root,
        pipeline_name="vectorization",
        descriptor=descriptor,
        descriptor_path=descriptor_path,
        skip=getattr(args, "no_audit", False),
    )
    if audit_ref:
        print(f"[vectorization] audit_event_ref={audit_ref}", file=sys.stderr)

    print(f"[vectorization] wrote {index_path} ({len(index_entries)} chunks, dim={result.dim})", file=sys.stderr)
    print(f"[vectorization] wrote {descriptor_path}", file=sys.stderr)
    if qdrant_info is not None:
        print(f"[vectorization] qdrant: {qdrant_info}", file=sys.stderr)
    return 0


SPEC = PipelineSpec(
    name="vectorization",
    description="Chunk + embed cleaned text; optional push to a local Qdrant collection (offline).",
    inputs=["text.clean.txt"],
    outputs=["index.json", "index.descriptor.json"],
    dependencies=["sentence-transformers>=2.7", "qdrant-client>=1.9", "jsonschema>=4.20"],
    output_pointer_template="derived/vectorization/{stem}.index.json",
    register=_register,
    run=_run,
)
