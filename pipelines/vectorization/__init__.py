"""Embedding + Qdrant indexing pipeline.

v0.5 stub. Full implementation tracked by issue #33.
"""
from __future__ import annotations

import argparse
import sys

from pipelines import PipelineSpec


def _register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--record", required=False, help="Path to the record directory.")
    parser.add_argument("--input", required=False, help="Path to a cleaned text file.")
    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Embedding model id. Default: all-MiniLM-L6-v2 (CPU friendly, offline once cached).",
    )
    parser.add_argument(
        "--qdrant-url",
        default="http://127.0.0.1:6333",
        help="Local Qdrant URL. Default: http://127.0.0.1:6333. Run "
             "'docker run -p 6333:6333 qdrant/qdrant' to start one.",
    )
    parser.add_argument(
        "--collection",
        default=None,
        help="Qdrant collection name. Defaults to the record id from manifest.json.",
    )


def _run(args: argparse.Namespace) -> int:
    print(
        "[vectorization] stub: embedding + Qdrant indexing pipeline scaffold "
        "from v0.5 issue #30. Real chunking + indexing arrives in issue #33.",
        file=sys.stderr,
    )
    return 0


SPEC = PipelineSpec(
    name="vectorization",
    description="Chunk + embed cleaned text and write to a local Qdrant collection (offline).",
    inputs=["text.clean.txt"],
    outputs=["vector_index.json"],
    dependencies=["sentence-transformers>=2.7", "qdrant-client>=1.9"],
    output_pointer_template="derived/vectorization/{stem}.index.json",
    register=_register,
    run=_run,
)
