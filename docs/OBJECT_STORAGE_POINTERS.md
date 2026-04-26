# DLRS Object Storage Pointer Specification (v0.3 Draft)

> **Status**: Draft for v0.3. This document satisfies issue
> [#11](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/11) and
> defines the canonical structure for all `*.pointer.json` files in a DLRS
> archive.

DLRS is **pointer-first**: raw sensitive materials (voice, video, images,
biometric scans, identity documents, etc.) MUST NOT be committed to a Git
repository. Only structured pointer files describing where the asset lives,
its integrity hash, sensitivity level, and access policy are stored in Git.

This specification covers:

1. Supported storage URI schemes
2. Required and optional pointer fields
3. Behavior specifications (retention, withdrawal, deletion, audit)
4. Security and access requirements
5. Concrete pointer examples
6. Relationship to `manifest.json` and the public registry

---

## 1. Supported Storage URI Schemes

A pointer's `storage_uri` MUST be a single absolute URI. The scheme
identifies the storage backend.

| Scheme    | Backend                                     | Example                                                                    |
| --------- | ------------------------------------------- | -------------------------------------------------------------------------- |
| `s3://`   | Amazon S3 (or S3-compatible)                | `s3://dlrs-private-vault/humans/asia/cn/dlrs_94f1c9b8/voice_master.wav`     |
| `oss://`  | Alibaba Cloud Object Storage Service        | `oss://dlrs-cn-shanghai/humans/asia/cn/dlrs_94f1c9b8/voice_master.wav`      |
| `cos://`  | Tencent Cloud Cloud Object Storage          | `cos://dlrs-ap-shanghai/humans/asia/cn/dlrs_94f1c9b8/voice_master.wav`      |
| `minio://`| MinIO or other self-hosted S3-compatible    | `minio://dlrs-onprem/humans/asia/cn/dlrs_94f1c9b8/voice_master.wav`         |
| `obj://`  | Generic / abstract object storage           | `obj://cn-shanghai/audio/voice_master.wav`                                  |
| `repo://` | Inside this Git repository (S0 only)        | `repo://public_profile.json`                                                |

**Rules**

- **No HTTP(S) public download URLs** in pointer files. Permanent public
  links are forbidden because they bypass access control and audit.
- Temporary signed URLs (e.g. presigned S3 URLs) are allowed at runtime but
  MUST NOT be persisted in `*.pointer.json`.
- The `repo://` scheme is reserved for assets that are explicitly approved
  for public storage (sensitivity `S0_PUBLIC`), e.g. `public_profile.json`
  or non-sensitive previews.
- Path segments SHOULD encode region, archive type, and `record_id` so that
  pointers stay traceable when archives are migrated.

---

## 2. Pointer Fields

### Required fields

| Field             | Type    | Description                                                                                |
| ----------------- | ------- | ------------------------------------------------------------------------------------------ |
| `storage_uri`     | string  | Absolute URI using one of the schemes above.                                               |
| `checksum`        | string  | Integrity hash. Format: `<algo>:<hex>`. SHA-256 is the default. Example `sha256:a1b2...`. |
| `region`          | string  | Storage region (e.g. `CN`, `cn-shanghai`, `us-west-2`). Used for residency enforcement.    |
| `format`          | string  | Container/format identifier (`wav`, `flac`, `mp4`, `png`, `glb`, `vrm`, `txt`, `json`).    |
| `sensitivity`     | string  | One of `S0_PUBLIC`, `S1_INTERNAL`, `S2_SENSITIVE`, `S3_BIOMETRIC`, `S4_RESTRICTED`.         |
| `access_policy`   | string  | Access control class. See [§4](#4-security-and-access-requirements).                       |

### Optional but strongly recommended

| Field                  | Type      | Description                                                                          |
| ---------------------- | --------- | ------------------------------------------------------------------------------------ |
| `artifact_type`        | string    | One of `audio`, `video`, `image`, `text`, `avatar_3d`, `document`, `embedding`.      |
| `size_bytes`           | integer   | Asset size for budgeting and quality checks.                                         |
| `encryption`           | object    | At-rest and in-transit encryption descriptors. See [§4](#4-security-and-access-requirements). |
| `retention_days`       | integer   | How long the asset is retained after upload.                                         |
| `withdrawal_supported` | boolean   | `true` if the storage backend supports record-level deletion within retention.       |
| `withdrawal_endpoint`  | string    | URL or `mailto:` for processing withdrawal requests targeting this asset.            |
| `consent_ref`          | string    | Repo-relative path to the consent evidence governing this asset.                     |
| `review_status`        | string    | One of `draft`, `submitted`, `approved`, `blocked`, `withdrawn`.                     |
| `media_metadata`       | object    | Per-artifact-type metadata (see [§3](#3-media-metadata-by-artifact-type)).           |
| `provenance`           | object    | Provenance / C2PA descriptors (`source`, `c2pa_manifest_uri`, `created_at`).         |

### Forbidden fields

| Field                | Reason                                                                       |
| -------------------- | ---------------------------------------------------------------------------- |
| `download_url`       | Permanent public links are forbidden.                                        |
| `presigned_url`      | Temporary URLs MUST NOT be persisted in `pointer.json`.                      |
| `password`           | Credentials MUST NEVER be embedded in pointer files.                         |
| `access_key_*`       | Credentials MUST NEVER be embedded in pointer files.                         |
| Raw biometric blobs  | Inline base64 of audio, video, images, or biometrics is forbidden.           |

---

## 3. Media Metadata by Artifact Type

Pointers describing media assets SHOULD include a `media_metadata` object
matching the artifact type. These fields feed into automated quality
validation (see `tools/validate_media.py`) and the
[Collection Standard](./COLLECTION_STANDARD.md).

### `audio`

```json
{
  "artifact_type": "audio",
  "media_metadata": {
    "duration_seconds": 600,
    "sample_rate_hz": 48000,
    "bit_depth": 24,
    "channels": 1,
    "loudness_lufs": -18.0,
    "true_peak_dbfs": -3.0,
    "codec": "pcm_s24le"
  }
}
```

### `video`

```json
{
  "artifact_type": "video",
  "media_metadata": {
    "duration_seconds": 90,
    "width": 1920,
    "height": 1080,
    "fps": 25,
    "codec": "h264",
    "container": "mp4"
  }
}
```

### `image`

```json
{
  "artifact_type": "image",
  "media_metadata": {
    "width": 2048,
    "height": 2048,
    "color_space": "sRGB",
    "format": "png"
  }
}
```

### `avatar_3d`

```json
{
  "artifact_type": "avatar_3d",
  "media_metadata": {
    "format": "vrm",
    "polygon_count": 50000,
    "rigged": true,
    "blendshape_set": "ARKit-52"
  }
}
```

### `text`

```json
{
  "artifact_type": "text",
  "media_metadata": {
    "language": "zh-CN",
    "character_count": 250000,
    "deidentified": true
  }
}
```

---

## 4. Security and Access Requirements

### Access policy values

| `access_policy`            | Meaning                                                                |
| -------------------------- | ---------------------------------------------------------------------- |
| `private_runtime_only`     | Asset only accessible to the owner-controlled runtime; never public.   |
| `team_internal`            | Accessible to authorized team members for processing/review.           |
| `audit_only`               | Read access strictly for audit/compliance roles.                       |
| `public_preview`           | Low-fidelity preview suitable for public listing (S0 only).            |

### Encryption descriptor

```json
{
  "encryption": {
    "at_rest": "AES-256",
    "in_transit": "TLS1.2+",
    "kms_ref": "kms://example/key-placeholder"
  }
}
```

- `at_rest`: encryption algorithm at rest (e.g. `AES-256`, `SSE-KMS`).
- `in_transit`: minimum TLS version for transport.
- `kms_ref`: opaque key reference; MUST NOT contain raw key material.

### Required behaviors

- **No permanent public download links**. Direct, unsigned access to S2+
  assets is forbidden. Runtime systems MUST mint short-lived signed URLs.
- **Audit logging**. Every read MUST emit an `audit-event` (see
  `schemas/audit-event.schema.json`) with `record_id`, `actor_role`, and
  `reason`.
- **Withdrawal**. If `withdrawal_supported` is `true`, the storage backend
  MUST be able to delete the underlying object on withdrawal request within
  the SLA defined in `policies/data-retention.md`.
- **Region residency**. The `region` field MUST match the
  `manifest.security.primary_region` (or be listed in
  `replication_regions`) unless an explicit
  `rights.cross_border_transfer_basis` permits otherwise.

---

## 5. Examples

### 5.1 Voice master (S3 biometric, biometric consent required)

```json
{
  "storage_uri": "s3://dlrs-private-vault/humans/asia/cn/dlrs_94f1c9b8/voice_master.wav",
  "checksum": "sha256:a1b2c3d4e5f6...",
  "region": "us-west-2",
  "format": "wav",
  "size_bytes": 98765432,
  "artifact_type": "audio",
  "sensitivity": "S3_BIOMETRIC",
  "access_policy": "private_runtime_only",
  "encryption": {
    "at_rest": "AES-256",
    "in_transit": "TLS1.2+",
    "kms_ref": "kms://example/voice-key"
  },
  "retention_days": 3650,
  "withdrawal_supported": true,
  "withdrawal_endpoint": "https://github.com/Digital-Life-Repository-Standard/DLRS/issues/new?template=consent-withdrawal.yml",
  "consent_ref": "consent/consent_statement.md",
  "review_status": "approved",
  "media_metadata": {
    "duration_seconds": 1800,
    "sample_rate_hz": 48000,
    "bit_depth": 24,
    "channels": 1,
    "loudness_lufs": -18.0,
    "true_peak_dbfs": -3.0,
    "codec": "pcm_s24le"
  },
  "provenance": {
    "source": "self_recorded",
    "created_at": "2026-04-25T10:30:00+08:00",
    "c2pa_manifest_uri": null
  }
}
```

### 5.2 Talking-head video (Tavus-style minimum)

```json
{
  "storage_uri": "oss://dlrs-cn-shanghai/humans/asia/cn/dlrs_94f1c9b8/talking_head_train.mp4",
  "checksum": "sha256:9876fedc...",
  "region": "cn-shanghai",
  "format": "mp4",
  "size_bytes": 234567890,
  "artifact_type": "video",
  "sensitivity": "S3_BIOMETRIC",
  "access_policy": "private_runtime_only",
  "encryption": {
    "at_rest": "AES-256",
    "in_transit": "TLS1.2+"
  },
  "retention_days": 3650,
  "withdrawal_supported": true,
  "consent_ref": "consent/consent_statement.zh-CN.md",
  "review_status": "approved",
  "media_metadata": {
    "duration_seconds": 90,
    "width": 1920,
    "height": 1080,
    "fps": 25,
    "codec": "h264",
    "container": "mp4"
  }
}
```

### 5.3 Public-profile asset (S0, stored in repo)

```json
{
  "storage_uri": "repo://public_profile.json",
  "checksum": "sha256:0000public...",
  "region": "global",
  "format": "json",
  "size_bytes": 4096,
  "artifact_type": "document",
  "sensitivity": "S0_PUBLIC",
  "access_policy": "public_preview",
  "review_status": "approved"
}
```

---

## 6. Relationship to `manifest.json`

- Each entry in `manifest.json#/artifacts` MUST point to a corresponding
  pointer file under `artifacts/raw_pointers/<type>/*.pointer.json`,
  `consent/*.pointer.json`, or `derived/*.pointer.json`.
- The pointer's `sensitivity` MUST match the manifest entry's `sensitivity`.
- Pointer files are validated against `schemas/pointer.schema.json` by
  `tools/validate_repo.py` and `tools/validate_media.py`.
- The public registry generator (`tools/build_registry.py`) MUST NOT
  surface fields from any pointer with `sensitivity` ≥ `S2_SENSITIVE`.

## 7. Related documents

- [`docs/COLLECTION_STANDARD.md`](./COLLECTION_STANDARD.md) — minimum media
  collection requirements.
- [`docs/HIGH_FIDELITY_GUIDE.md`](./HIGH_FIDELITY_GUIDE.md) — aspirational
  guidelines for professional-grade archives.
- [`policies/privacy.md`](../policies/privacy.md) — privacy boundaries.
- [`policies/data-retention.md`](../policies/data-retention.md) — retention
  and withdrawal SLAs.
- `schemas/pointer.schema.json` — machine-checkable pointer schema.
