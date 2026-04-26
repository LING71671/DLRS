"""Built-in moderation policies for the offline-first pipeline.

Design principles, mirroring :mod:`pipelines.text.cleaning`:

- **Deterministic.** Same input → same flags. No LLM call. No remote
  taxonomy lookup. The pipeline must be reproducible with no network.
- **Conservative.** The default lexicons are intentionally small and
  high-precision. False positives are easier to forgive than false
  negatives, but the cure for under-flagging is a richer custom policy
  passed via ``--policy-file``, NOT a noisier default.
- **Auditable.** Every flag carries the *rule name* and a char span,
  but never the matched substring itself, so ``moderation.json`` cannot
  become a secondary leak vector for the very content it is moderating.

Custom policies (JSON or YAML) follow this shape::

    {
      "rules": [
        {
          "name": "ja_slur_example",
          "category": "hate",
          "severity": "high",
          "patterns": ["\\\\bword1\\\\b", "word2"]
        }
      ]
    }

``severity`` is one of ``"low" | "medium" | "high"``. Outcome rules:

- any ``high`` flag → ``block``
- otherwise any ``medium`` flag → ``flag``
- otherwise (only ``low`` or no flags) → ``pass``
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

POLICY_VERSION = "1.0"

VALID_SEVERITY = ("low", "medium", "high")


@dataclass(frozen=True)
class Rule:
    """A single moderation rule."""

    name: str
    category: str
    severity: str  # low | medium | high
    patterns: tuple[re.Pattern[str], ...]

    @classmethod
    def from_dict(cls, raw: dict) -> "Rule":
        if "name" not in raw or "patterns" not in raw:
            raise ValueError(f"rule missing 'name' or 'patterns': {raw!r}")
        severity = raw.get("severity", "medium")
        if severity not in VALID_SEVERITY:
            raise ValueError(f"rule {raw['name']!r}: severity must be one of {VALID_SEVERITY}, got {severity!r}")
        category = raw.get("category", "custom")
        compiled = tuple(re.compile(p, re.IGNORECASE | re.UNICODE) for p in raw["patterns"])
        return cls(
            name=raw["name"],
            category=category,
            severity=severity,
            patterns=compiled,
        )


@dataclass(frozen=True)
class Flag:
    """A moderation match. Never carries the original substring."""

    rule_name: str
    category: str
    severity: str
    start: int
    end: int

    def to_dict(self) -> dict:
        return {
            "rule": self.rule_name,
            "category": self.category,
            "severity": self.severity,
            "start": self.start,
            "end": self.end,
        }


@dataclass
class Policy:
    """A bundle of rules. ``__call__`` returns the flags found in text."""

    name: str
    version: str
    rules: List[Rule] = field(default_factory=list)

    def scan(self, text: str) -> List[Flag]:
        flags: List[Flag] = []
        for rule in self.rules:
            for pat in rule.patterns:
                for m in pat.finditer(text):
                    flags.append(
                        Flag(
                            rule_name=rule.name,
                            category=rule.category,
                            severity=rule.severity,
                            start=m.start(),
                            end=m.end(),
                        )
                    )
        flags.sort(key=lambda f: (f.start, f.end, f.rule_name))
        return flags


def outcome_for(flags: Iterable[Flag]) -> str:
    """Return 'block' / 'flag' / 'pass' per the severity-aggregation rule."""
    severities = {f.severity for f in flags}
    if "high" in severities:
        return "block"
    if "medium" in severities:
        return "flag"
    return "pass"


# --------------------------------------------------------------------------- #
# Built-in (intentionally small, high-precision) policy                        #
# --------------------------------------------------------------------------- #

_BUILTIN_POLICY_DICT = {
    "name": "dlrs-builtin/v0.5",
    "version": POLICY_VERSION,
    "rules": [
        # Self-harm: high severity. The English wordlist below is small and
        # explicit; detection biases toward intent verbs paired with self
        # references. Adjust via --policy-file for richer multilingual coverage.
        {
            "name": "self_harm_intent_en",
            "category": "self_harm",
            "severity": "high",
            "patterns": [
                r"\b(?:kill|hurt|harm|cut)\s+myself\b",
                r"\bend\s+my\s+life\b",
                r"\bsuicide\s+(?:plan|note|method)\b",
            ],
        },
        # Direct violent threats. Same shape, conservative.
        {
            "name": "violence_threat_en",
            "category": "violence",
            "severity": "high",
            "patterns": [
                r"\b(?:kill|murder|stab|shoot)\s+(?:you|him|her|them)\b",
                r"\bI\s+will\s+(?:kill|murder|hurt)\s+\w+",
            ],
        },
        # PII that the text-cleaning redactor (#32) would have caught — kept
        # as a moderation rule too so an end-to-end run that skips the text
        # pipeline still gets a 'flag' outcome rather than silent passage.
        {
            "name": "pii_email_residual",
            "category": "pii_residual",
            "severity": "medium",
            "patterns": [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"],
        },
        {
            "name": "pii_phone_cn_residual",
            "category": "pii_residual",
            "severity": "medium",
            "patterns": [r"(?<!\d)1[3-9]\d{9}(?!\d)"],
        },
        # Profanity (English): short list of unambiguous slurs / vulgarities.
        # Intentionally non-exhaustive. We tag low-severity so the default
        # outcome stays 'pass' unless co-occurring with something stronger.
        {
            "name": "profanity_basic_en",
            "category": "profanity",
            "severity": "low",
            "patterns": [
                r"\bfuck(?:ing|ed)?\b",
                r"\bshit\b",
                r"\bbitch\b",
            ],
        },
    ],
}


def builtin_policy() -> Policy:
    """Return a fresh instance of the built-in v0.5 policy."""
    return Policy(
        name=_BUILTIN_POLICY_DICT["name"],
        version=_BUILTIN_POLICY_DICT["version"],
        rules=[Rule.from_dict(r) for r in _BUILTIN_POLICY_DICT["rules"]],
    )


def load_policy_file(path: Path) -> Policy:
    """Load a custom policy from JSON. (YAML support requires PyYAML; if the
    user passes a .yaml file we surface a clean error instead of silently
    misreading.)"""
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise SystemExit(
                f"[moderation] {path} requires PyYAML; install with "
                "'pip install PyYAML' or convert the file to JSON."
            ) from exc
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "rules" not in raw:
        raise SystemExit(f"[moderation] {path} is not a valid policy (missing 'rules')")
    rules = [Rule.from_dict(r) for r in raw["rules"]]
    return Policy(
        name=raw.get("name", path.stem),
        version=str(raw.get("version", "user-supplied")),
        rules=rules,
    )


def merge_policies(*policies: Policy) -> Policy:
    """Merge multiple policies into one. Later policies append rules; rules
    with duplicate ``name`` are kept verbatim so the audit trail is still
    explicit about which rule fired."""
    merged_rules: List[Rule] = []
    parts = []
    for p in policies:
        merged_rules.extend(p.rules)
        parts.append(f"{p.name}@{p.version}")
    return Policy(
        name="+".join(parts) or "empty",
        version=POLICY_VERSION,
        rules=merged_rules,
    )


def select_policy(*, use_builtin: bool, custom_path: Optional[Path]) -> Policy:
    parts = []
    if use_builtin:
        parts.append(builtin_policy())
    if custom_path is not None:
        parts.append(load_policy_file(custom_path))
    if not parts:
        raise SystemExit(
            "[moderation] no policy selected: pass --no-builtin only when "
            "--policy-file points at a custom policy."
        )
    return parts[0] if len(parts) == 1 else merge_policies(*parts)
