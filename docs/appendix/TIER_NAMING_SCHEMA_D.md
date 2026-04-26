# Tier Naming Appendix — Schema D (Cosmic Evolution)

**Status**: normative for v0.8 \
**Versioned independently from `docs/LIFE_TIER_SPEC.md`** —
naming-appendix revisions MAY ship without a spec major bump.
Consumers MUST treat the Roman-numeral `level` (I–XII) as the
canonical machine identifier; `name` and `glyph` are presentation-
layer aliases sourced from this appendix.

## Why Schema D

The user-locked theme for the tier naming layer is **sci-fi / AI / data
/ cosmic** (议题 3, Q2). Five candidate schemes were reviewed
during the v0.8 architecture discussion:

| Schema | Ordering | Imagery | Rejected because |
|---|---|---|---|
| A — Moon phases | 12 phases | culturally shared | reads as mystical / horoscopic for a technical credit rating |
| B — Minerals (Mohs hardness) | 12 minerals | natural ordering | tier-XI/XII names (Lonsdaleite, Carbonado) too obscure |
| C — Pure geometric glyphs | 12 abstract symbols | culturally neutral | abstract, not memorable for social use |
| E — Data architecture (Bit → Singularity) | 12 data terms | engineering-native | Bit / Nibble / Byte too low-level for a social-facing concept |
| F — Hybrid Data → Cosmic (Bit → Tensor → Galaxy → Singularity) | 12 mixed | bridges data + cosmos | requires the reader to span two domains; not as clean as D |
| **D — Cosmic Evolution (Quark → Singularity)** | **12 emergent steps** | **physics-native, sci-fi friendly** | **chosen** |

Schema D maps `.life` package strength to cosmological emergence:
the lowest tier is sub-atomic, the highest is a singularity. The
ordering is monotonic and physically motivated — every tier is
"more emergent" than the previous one — which gives the credit-
rating semantics a natural intuition bridge.

## Tier table (canonical, v0.8)

| Level | Name | 中文 | Glyph | Score range | Cosmological reading |
|---|---|---|---|---|---|
| I | Quark | 夸克 | ⋅ | 0–8 | sub-atomic, no structure yet |
| II | Atom | 原子 | ⊙ | 9–16 | minimal stable structure |
| III | Molecule | 分子 | ⋮⋮ | 17–24 | composition begins |
| IV | Stardust | 星尘 | ✧ | 25–32 | ingredients of a system but unbound |
| V | Nebula | 星云 | 🌫 | 33–40 | gravitational organization starting |
| VI | Protostar | 原恒星 | ✦ | 41–50 | self-sustaining process forming |
| VII | Main Sequence | 主序星 | ★ | 51–60 | healthy steady-state — the social-target tier |
| VIII | Red Giant | 红巨星 | ◉ | 61–68 | mature, expanded, full-bodied |
| IX | White Dwarf | 白矮星 | ⚪ | 69–76 | dense, compact, long-lived |
| X | Neutron Star | 中子星 | ⚫ | 77–84 | extreme density, rare |
| XI | Pulsar | 脉冲星 | ◎ | 85–92 | precise, observable, well-attested |
| XII | Singularity | 奇点 | ● | 93–100 | end-state — full archive-grade `.life` |

Score boundaries are **inclusive on both ends**. The boundaries are
chosen so:

- Each tier covers either 8 or 9 score-points in the lower half (I–V
  span 0–40 in five tiers of 8–9 points).
- Tier VI–VII are slightly wider (10 points each) to make
  "Main Sequence" a comfortable steady-state band — a healthy
  comprehensive `.life` lands in VII without needing exotic perfection.
- Tiers X–XII narrow again (8 points each) so the top tiers are
  rare and meaningful.

## Compliance rules

A `.life` builder claiming Schema D MUST satisfy all of:

1. **Canonical names** — the `name` field is exactly the value in the
   "Name" column above for the corresponding `level`. No translation
   is performed at build time; localisation is a UI-layer concern.
2. **Canonical glyphs** — the `glyph` field is exactly the value in
   the "Glyph" column above. UI consumers MAY substitute alternative
   glyphs for accessibility (e.g. high-contrast or text-only
   variants), but the in-package glyph MUST be the canonical one so
   downstream verifiers can reproduce the build.
3. **Score → level binding** — the schema enforces this via
   `allOf/if/then` rules; see `schemas/tier.schema.json::tier_block`.

## Future appendices

This file is **Schema D / v0.8.0**. Future naming schemes (e.g. a
hypothetical Schema G — "Music notation tiers") MAY ship as a sibling
appendix file under `docs/appendix/TIER_NAMING_SCHEMA_<X>.md`. The
machine-readable `level` field MUST remain backwards-compatible
(I–XII Roman numerals) so a Schema-G `.life` and a Schema-D `.life`
remain comparable at the machine level.

A `.life` MUST declare which appendix is in force — for v0.8 every
package implicitly uses Schema D because no other appendix exists
yet. From v0.9 onwards, an explicit `naming_schema_id` field in the
tier block MAY be added (deferred to v0.9 design review).

## Source of truth

This appendix is the source of truth for the human-facing tier
labels. The architecture overview (`docs/LIFE_ASSET_ARCHITECTURE.md`
§5 + appendix A) summarises the same table for context but defers
to this appendix in case of any drift.
