"""DLRS reference runtime — `life-runtime v0.1.1` reference implementation.

This package implements the protocol defined in
``docs/LIFE_RUNTIME_STANDARD.md`` (v0.7 §1-10 + v0.8 Part B 5-stage assembly).

Public surface today (v0.9 sub-issue #120 — scaffold only):

- ``__version__`` — runtime package version (``0.9.0.dev0``).
- ``LIFE_RUNTIME_PROTOCOL_VERSION`` — declared life-runtime spec version.
- ``Runtime`` — placeholder class; concrete assembly stages land in sub-issues
  #121-#126.

The ``runtime.cli.lifectl`` module exposes the ``lifectl`` console script.
"""

from __future__ import annotations

__version__ = "0.9.0.dev0"
LIFE_RUNTIME_PROTOCOL_VERSION = "0.1.1"


class Runtime:
    """Stub Runtime class. Concrete behaviour added in sub-issues #121-#126."""

    def __init__(self) -> None:
        self.version = __version__
        self.protocol = LIFE_RUNTIME_PROTOCOL_VERSION

    def __repr__(self) -> str:
        return (
            f"Runtime(version={self.version!r}, "
            f"protocol={self.protocol!r}, stages_implemented=[])"
        )


__all__ = ["__version__", "LIFE_RUNTIME_PROTOCOL_VERSION", "Runtime"]
