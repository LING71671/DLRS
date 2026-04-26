"""Deterministic text normalisation and conservative sensitive-info redaction.

Design principles:

- **Deterministic.** Same input → same output, byte-for-byte. No language
  models, no probabilistic heuristics. The pipeline must be reproducible
  on a laptop with no network access.
- **Conservative.** Better to over-redact than to leak. The redactor uses
  high-precision regex patterns; anything that is genuinely ambiguous
  (free-form addresses, names, dates of birth) is intentionally left for
  v0.6's NER-based redactor.
- **Auditable.** ``redact()`` returns a list of (kind, char-span,
  replacement_token) triples without echoing the original sensitive
  substring back. Reviewers can verify counts and positions without the
  redactions.json file becoming a secondary leak vector.

Supported kinds (initial v0.5 set):

- ``email``           generic RFC-5322-style addresses
- ``phone_cn``        Chinese mainland mobile (11 digits starting 1[3-9])
- ``phone_generic``   loose international / landline numbers
- ``id_cn``           18-digit Chinese national ID (last char optional X)
- ``ipv4``            dotted-quad IPv4 addresses
- ``credit_card_like`` 16-digit groups (catch-all; conservative)
- ``url_with_credentials`` URLs containing ``user:password@`` segments

Redactions are replaced with stable placeholders so that downstream
embeddings still see structure (``<EMAIL>``, ``<PHONE>``, …) rather than
random noise.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple

NORMALISER_VERSION = "1.0"
REDACTOR_VERSION = "1.0"


# --------------------------------------------------------------------------- #
# Normalisation                                                                #
# --------------------------------------------------------------------------- #

# Match runs of ASCII / Unicode whitespace EXCEPT a literal newline so we keep
# paragraph structure. ``\u3000`` is the CJK ideographic space.
_HORIZONTAL_WS = re.compile(r"[ \t\u00a0\u2000-\u200a\u202f\u205f\u3000]+")
_TRAILING_WS = re.compile(r"[ \t]+\n")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_ZERO_WIDTH = re.compile(r"[\u200b-\u200d\ufeff]")


def normalise(text: str) -> str:
    """Apply NFKC + whitespace canonicalisation.

    Steps (in order):

    1. ``unicodedata.normalize("NFKC", text)`` — collapses fullwidth /
       ligature variants so ``ＡＢＣ`` and ``ABC`` hash the same.
    2. Strip zero-width chars (``U+200B``-``U+200D``, BOM).
    3. Convert ``\\r\\n`` / ``\\r`` to ``\\n``.
    4. Collapse runs of horizontal whitespace to a single space.
    5. Drop trailing whitespace before each newline.
    6. Collapse 3+ consecutive newlines to exactly two (paragraph break).
    7. Strip leading/trailing whitespace from the whole document.
    """
    text = unicodedata.normalize("NFKC", text)
    text = _ZERO_WIDTH.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HORIZONTAL_WS.sub(" ", text)
    text = _TRAILING_WS.sub("\n", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------- #
# Redaction                                                                    #
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Redaction:
    """A single redaction event. Never carries the original substring."""

    kind: str
    start: int
    end: int
    replacement: str

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "start": self.start,
            "end": self.end,
            "replacement": self.replacement,
        }


# Order matters: more specific patterns run first so a Chinese ID (18 digits)
# is not stolen by the credit-card-like 16-digit pattern.
_REDACTION_RULES: List[Tuple[str, re.Pattern[str], str]] = [
    (
        "url_with_credentials",
        re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/@]+:[^\s/@]+@[^\s]+"),
        "<URL_WITH_CREDENTIALS>",
    ),
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "<EMAIL>",
    ),
    (
        "id_cn",
        re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
        "<ID_CN>",
    ),
    (
        "phone_cn",
        re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
        "<PHONE_CN>",
    ),
    (
        "ipv4",
        re.compile(
            r"(?<!\d)(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
            r"(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}(?!\d)"
        ),
        "<IPV4>",
    ),
    (
        "credit_card_like",
        # 13-19 digit runs that may contain spaces or hyphens. Validated
        # loosely (no Luhn check — false negatives are unacceptable).
        re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
        "<CARD>",
    ),
    (
        "phone_generic",
        # Loose: a leading + or digit, then 7-15 digits with optional
        # separators. Runs LAST so country-specific patterns above win.
        re.compile(r"(?<!\d)\+?\d[\d \-().]{6,18}\d(?!\d)"),
        "<PHONE>",
    ),
]


def redact(text: str) -> Tuple[str, List[Redaction]]:
    """Return (cleaned_text, redactions).

    Redactions are applied left-to-right; once a span is replaced the
    later rules see the placeholder and cannot match across it.
    """
    redactions: List[Redaction] = []
    out_chunks: List[str] = []
    cursor = 0
    # Combine all rules into one walk so positions are tracked correctly.
    while cursor < len(text):
        best: Tuple[int, int, str, str] | None = None  # (start, end, kind, replacement)
        for kind, pattern, replacement in _REDACTION_RULES:
            m = pattern.search(text, cursor)
            if m is None:
                continue
            if best is None or m.start() < best[0]:
                best = (m.start(), m.end(), kind, replacement)
        if best is None:
            out_chunks.append(text[cursor:])
            break
        start, end, kind, replacement = best
        out_chunks.append(text[cursor:start])
        # Translate the replacement's char span back to the *output* offsets
        # so the redactions JSON is consumable without rebuilding the
        # original string. We compute the offset in the (so-far) output.
        out_start = sum(len(c) for c in out_chunks)
        out_chunks.append(replacement)
        out_end = out_start + len(replacement)
        redactions.append(Redaction(kind=kind, start=out_start, end=out_end, replacement=replacement))
        cursor = end
    return "".join(out_chunks), redactions


def clean(
    text: str,
    *,
    do_normalise: bool = True,
    do_redact: bool = True,
) -> Tuple[str, List[Redaction]]:
    """High-level entry point used by ``pipelines.text``."""
    if do_normalise:
        text = normalise(text)
    redactions: List[Redaction] = []
    if do_redact:
        text, redactions = redact(text)
    return text, redactions
