# DLRS Minimum Collection Standard (v0.3 Draft)

> **Status**: Draft for v0.3. This document satisfies issue
> [#8](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/8) and
> defines the **minimum viable** material requirements for contributing a
> DLRS-compatible digital life archive.
>
> For aspirational, professional-grade collection guidance see
> [`docs/HIGH_FIDELITY_GUIDE.md`](./HIGH_FIDELITY_GUIDE.md).

DLRS is a privacy-first standard. The collection standard exists to ensure
that:

1. Contributed materials are **technically usable** by future processing
   pipelines (ASR, voice cloning, talking-head, etc.).
2. Collection is **legally defensible** (consent, residency, deceased-rights).
3. The repository **only stores pointers**, never raw biometric content.

If you are unsure whether your archive can meet these minimums, **do not
upload anything** — open a discussion first.

---

## 0. Hard Rules (apply to all media types)

- **Raw sensitive materials MUST NOT be committed to GitHub.** This includes
  voice recordings, video, ID-document scans, identifiable photos, and any
  biometric blobs. Only `*.pointer.json` files describing these assets may
  live in Git.
- **Every record MUST have a signed consent statement** in `consent/` (see
  [`templates/consent/`](../templates/consent/)). For voice/avatar/biometric
  use, a **separate biometric consent** is required (see the consent
  schema's `separate_biometric_consent` flag).
- **Every record MUST publish a working `withdrawal_endpoint`** in
  `manifest.json#/consent/withdrawal_endpoint`. This is how subjects
  exercise the right to withdraw.
- **Pointer files MUST follow** the
  [Object Storage Pointer Specification](./OBJECT_STORAGE_POINTERS.md).
- **Naming convention** for pointer files:
  `artifacts/raw_pointers/<artifact_type>/<asset>_<descriptor>.pointer.json`
  (e.g. `artifacts/raw_pointers/audio/voice_master.pointer.json`).
- **Sensitivity labelling**: any media depicting an identifiable person's
  face, voice, or biometric features MUST be marked at least
  `S3_BIOMETRIC`. Identity-document scans MUST be marked `S4_RESTRICTED`.
- **Minors**: archives where `subject.is_minor=true` MUST NOT be public,
  MUST have guardian consent, and MUST set
  `review.risk_level >= "high"`.
- **Deceased subjects**: archives where `subject.status="deceased"` MUST
  follow [`policies/deceased-persons.md`](../policies/deceased-persons.md)
  and MUST set `inheritance_policy.default_action_on_death`.

---

## 1. Audio / Voice Collection — Minimum

| Field                | Minimum                                  |
| -------------------- | ---------------------------------------- |
| Format               | `wav`, `flac`, or `mp3 ≥ 192kbps`        |
| Sample rate          | ≥ 44 100 Hz                              |
| Bit depth            | ≥ 16-bit                                 |
| Channels             | Mono preferred; stereo allowed           |
| Total duration       | ≥ 60 seconds of clean speech             |
| Loudness             | Peak ≤ -3 dBFS, integrated near -18 LUFS |
| Background noise     | < -50 dBFS RMS                           |
| Recording environment| Quiet room, no echo, single speaker      |

**Pointer fields required**: `media_metadata.duration_seconds`,
`sample_rate_hz`, `bit_depth`, `channels`, `format`.

**Common rejections**

- Very short clips (< 60 s).
- Heavy room reverb / echo.
- Aggressive noise suppression that destroys partials.
- Multiple speakers in the same recording.

---

## 2. Video / Talking-head Collection — Minimum

| Field                | Minimum                                            |
| -------------------- | -------------------------------------------------- |
| Format               | `mp4` (H.264) or `mov`                             |
| Resolution           | ≥ 1280×720 (HD); 1920×1080 strongly recommended    |
| Frame rate           | ≥ 24 fps                                           |
| Duration             | ≥ 30 s of continuous talking + 30 s of stillness   |
| Camera angle         | Front, plus 3/4 view                               |
| Subject framing      | Face occupies ≥ 25% of frame                       |
| Lighting             | Even, no hard shadows on the face                  |
| Background           | Static, uncluttered                                |

**Pointer fields required**: `media_metadata.width`, `height`, `fps`,
`duration_seconds`, `codec`, `container`.

**Forbidden in the same recording**

- Multiple identifiable people (Tavus-style replicas require a single
  subject).
- Hard cuts, zooms, or camera motion.
- Visible text overlays / lower-thirds.

---

## 3. Images / Avatar Reference Collection — Minimum

| Field                | Minimum                                  |
| -------------------- | ---------------------------------------- |
| Format               | `png` or `jpg`                           |
| Resolution           | ≥ 512×512 per image                      |
| Quantity             | ≥ 5 photos covering required angles      |
| Required angles      | Front, left 3/4, right 3/4, side, top    |
| Quality              | Sharp focus, neutral expression          |

**Pointer fields required**: `media_metadata.width`, `height`, `format`.

---

## 4. Text / Chat / History Corpus — Minimum

| Field                | Minimum                                         |
| -------------------- | ----------------------------------------------- |
| Source               | Self-authored: writings, emails, chat exports   |
| Authorization        | Subject (or estate) has written rights to text  |
| De-identification    | Third-party PII MUST be redacted before commit  |
| Format               | UTF-8 plain text or JSONL                       |
| Volume               | ≥ 10 000 characters of subject-authored text    |
| Provenance           | Each chunk MUST record `source` and timestamp   |

**Important**: Even though text is less obviously biometric than voice or
face, **chat logs and personal correspondence are still S2_SENSITIVE**.
Pointer-only storage and runtime-only access apply.

---

## 5. 3D Avatar Asset Collection — Minimum

| Field                | Minimum                                         |
| -------------------- | ----------------------------------------------- |
| Format               | `vrm`, `glb`/`gltf`, `fbx`, or `obj`            |
| Mesh                 | Watertight, no inverted normals                 |
| Texture              | At minimum: base colour map (≥ 1024×1024)       |
| Rigging              | Optional for static reference; required for animation |
| Blendshapes          | Optional; if present, document the set used     |

**Pointer fields required**: `media_metadata.format`, `polygon_count`.

---

## 6. Consent Evidence — Minimum

For every archive, the `consent/` directory MUST contain at least:

- `consent_statement.<lang>.md` — signed statement (text version).
- `consent_video.pointer.json` (recommended) — pointer to a short video in
  which the subject states their name, the date, and the scope of consent.
- `signer_signature.json` — structured signer metadata.

If any biometric scope is enabled (`allow_voice_clone`, `allow_avatar_clone`,
or storage of S3+ assets), **the consent statement MUST explicitly mention
voice/face cloning and biometric storage** and the manifest's
`consent.separate_biometric_consent` MUST be `true`.

---

## 7. Pointer Naming Conventions

```
artifacts/raw_pointers/
├── audio/
│   ├── voice_master.pointer.json
│   └── voice_emotion_<scenario>.pointer.json
├── video/
│   ├── talking_head_train.pointer.json
│   └── full_body_train.pointer.json
├── image/
│   ├── headshot_front.pointer.json
│   └── headshot_<angle>.pointer.json
├── text/
│   └── corpus_<source>.pointer.json
└── avatar_3d/
    └── avatar_base.pointer.json
```

Within `media_metadata`, use snake_case and SI units (`duration_seconds`,
`sample_rate_hz`, `width`, `height`).

---

## 8. Validation Checklist

A record is **collection-compliant** when all of the following hold:

- [ ] No raw media files committed (`tools/check_sensitive_files.py` passes).
- [ ] Every artifact in `manifest.json#/artifacts` has a matching
      `*.pointer.json` file.
- [ ] Every pointer validates against `schemas/pointer.schema.json`.
- [ ] Every pointer's `media_metadata` meets the minimums in §1–§5.
- [ ] `consent/` contains a signed statement and (if biometrics are in
      scope) a biometric consent video pointer.
- [ ] `manifest.json#/consent/withdrawal_endpoint` is reachable.
- [ ] `tools/validate_repo.py` and `tools/validate_media.py` exit 0.

CI runs `tools/validate_repo.py`, `tools/validate_media.py`, and
`tools/test_registry.py` on every push and PR.

---

## 9. Related documents

- [`docs/OBJECT_STORAGE_POINTERS.md`](./OBJECT_STORAGE_POINTERS.md) —
  pointer specification.
- [`docs/HIGH_FIDELITY_GUIDE.md`](./HIGH_FIDELITY_GUIDE.md) — aspirational
  high-fidelity collection guide.
- [`policies/privacy.md`](../policies/privacy.md) — privacy boundary.
- [`policies/risk-levels.md`](../policies/risk-levels.md) — risk
  classification.
- [`templates/consent/`](../templates/consent/) — consent templates.
