"""DLRS build pipelines.

This package hosts the offline-first build pipelines that turn raw artefacts
(audio, images, text) referenced by ``manifest.json`` into derived artefacts
that runtime layers can consume (transcripts, cleaned text, embeddings,
moderation reports).

Every pipeline MUST:

1. Be runnable on a single laptop with no hosted API access.
2. Declare a :class:`PipelineSpec` so ``tools/run_pipeline.py`` can dispatch it.
3. Lazy-import any optional heavy dependency (whisper, qdrant, sentence
   transformers, …) so ``--help`` works on a bare Python install.
4. Emit derived artefacts under ``<record>/derived/<pipeline>/`` and a
   companion derived-asset descriptor (``schemas/derived-asset.schema.json``,
   added in v0.5 follow-up issues).

Sub-packages:

- :mod:`pipelines.asr`           - speech recognition (faster-whisper default)
- :mod:`pipelines.text`          - normalisation + sensitive-info redaction
- :mod:`pipelines.vectorization` - embedding + local Qdrant indexing
- :mod:`pipelines.moderation`    - offline lexicon + cross-border block
- :mod:`pipelines.memory_atoms`  - long-term-memory atom extraction (v0.6)
"""
from __future__ import annotations

import argparse
import importlib
from dataclasses import dataclass, field
from typing import Callable, List


@dataclass(frozen=True)
class PipelineSpec:
    """Static metadata describing a pipeline.

    The metadata exists so that tooling (``tools/run_pipeline.py``,
    ``tools/validate_pipelines.py``, future audit emitters) can introspect a
    pipeline without importing its heavy dependencies.

    Attributes:
        name: Short identifier used as the CLI subcommand
            (``run_pipeline.py asr``, ``run_pipeline.py text`` …).
        description: One-line human-readable description.
        inputs: Logical input artefact kinds this pipeline consumes
            (e.g. ``["audio.wav", "audio.mp3"]``).
        outputs: Logical output artefact kinds this pipeline produces
            (e.g. ``["transcript.json"]``).
        dependencies: Optional third-party Python packages required at
            runtime. The CLI must NOT import these at module import time;
            they are listed here purely for documentation and validation.
        output_pointer_template: Relative path under a record directory
            where the canonical output is written. ``{stem}`` is replaced
            with the input filename stem.
        register: Callable that registers pipeline-specific CLI flags on a
            sub-parser (``register(subparser)``).
        run: Callable that executes the pipeline. Returns a process exit
            code (``0`` on success).
    """

    name: str
    description: str
    inputs: List[str]
    outputs: List[str]
    dependencies: List[str]
    output_pointer_template: str
    register: Callable[[argparse.ArgumentParser], None]
    run: Callable[[argparse.Namespace], int]
    online_apis_used: List[str] = field(default_factory=list)


# Names of the sub-packages that ship a ``SPEC`` constant. Kept explicit so
# ``run_pipeline.py --list`` has a deterministic ordering and so dynamically
# discovering pipelines doesn't require walking the filesystem.
PIPELINE_MODULES: List[str] = [
    "pipelines.asr",
    "pipelines.text",
    "pipelines.vectorization",
    "pipelines.moderation",
    "pipelines.memory_atoms",
]


def load_specs() -> List[PipelineSpec]:
    """Import each pipeline module and return its :class:`PipelineSpec`.

    Imports are performed lazily here (not at package import time) so that
    importing :mod:`pipelines` itself does not pull in heavy optional
    dependencies. Each sub-module MUST define a module-level ``SPEC``
    attribute of type :class:`PipelineSpec`.
    """
    specs: List[PipelineSpec] = []
    for mod_name in PIPELINE_MODULES:
        module = importlib.import_module(mod_name)
        spec = getattr(module, "SPEC", None)
        if not isinstance(spec, PipelineSpec):
            raise RuntimeError(
                f"{mod_name} does not export a PipelineSpec named SPEC"
            )
        specs.append(spec)
    return specs
