# DLRS High-Fidelity Collection Guide (v0.3 Draft)

> **Status**: Draft for v0.3. Satisfies issue
> [#15](https://github.com/Digital-Life-Repository-Standard/DLRS/issues/15)
> and extends the [Minimum Collection Standard](./COLLECTION_STANDARD.md)
> with aspirational guidance for professional-grade archives.

The minimum standard makes records *technically usable*. This guide
describes what it takes to make records *production-grade* — closer to the
quality bar referenced by Tavus Replica training and ElevenLabs
professional voice cloning.

These targets are **NOT required for v0.3 launch** — they are recommended
for contributors who can afford studio-quality capture.

---

## 1. Audio / Voice — High-Fidelity Tier

| Tier              | Minimum (§1) | Mid-fidelity         | High-fidelity                |
| ----------------- | ------------ | -------------------- | ---------------------------- |
| Sample rate       | 44.1 kHz     | 48 kHz               | 96–192 kHz                   |
| Bit depth         | 16-bit       | 24-bit               | 24- or 32-bit float          |
| Total duration    | ≥ 60 s       | 30–60 minutes        | 30–180 minutes               |
| Mic               | Consumer USB | Cardioid condenser   | Large-diaphragm condenser    |
| Room              | Quiet room   | Treated room         | Acoustically treated booth   |
| Loudness          | -18 LUFS     | -18 LUFS, ±1 LU      | -18 LUFS, ±0.5 LU            |
| Sessions          | 1            | 2–3 sessions         | Multiple emotion / scenario sessions |

**Recording scenarios** (high-fidelity)

- Conversational reading (news / book passages).
- Emotional range: neutral, happy, sad, angry, surprised.
- Sustained vowels for pitch / vibrato modelling.
- Reading numerical / technical content for pronunciation coverage.
- Optional: singing or humming (clearly labelled).

**Acoustic treatment**

- Broadband absorption on first reflections.
- Bass traps in corners.
- Floor coverings to reduce reflections from below.
- Avoid rooms with parallel walls.

---

## 2. Video / Talking-head — High-Fidelity Tier

| Tier              | Minimum (§2) | Mid-fidelity         | High-fidelity                |
| ----------------- | ------------ | -------------------- | ---------------------------- |
| Resolution        | 1280×720     | 1920×1080            | 3840×2160 (4K) or higher     |
| Frame rate        | 24 fps       | 25–30 fps            | 60–120 fps                   |
| Bitrate           | best-effort  | ≥ 20 Mbps            | ≥ 80 Mbps or visually lossless |
| Lighting          | Even ambient | Key + fill           | Three-point + practical fills |
| Camera            | Phone OK     | Mirrorless           | Cinema camera, calibrated     |
| Lens              | Phone        | 35–50 mm equivalent  | 50–85 mm prime, low distortion |
| Capture sessions  | 1            | 2–3 wardrobe / pose changes | Multi-day, multi-scenario, multi-camera |
| Audio             | Camera mic   | Lav mic              | Lav + boom + room reference   |

**Scenarios**

- Static talking head (front + 3/4).
- Conversational gestures (no walking).
- Idle / silent moments (≥ 60 s) for stillness modelling.
- Optional: full-body / posture clips for future avatar work.

**Post**

- Colour-managed pipeline (Rec.709 minimum, ACES recommended).
- Proxy generation for downstream pipelines.
- Edit decision lists / EDL preserved alongside masters.

---

## 3. Images / Reference Photography — High-Fidelity Tier

| Tier              | Minimum (§3)        | High-fidelity                       |
| ----------------- | ------------------- | ----------------------------------- |
| Format            | `png`/`jpg`         | RAW (`dng`/`cr3`/`nef`) + processed `tif`/`png` |
| Resolution        | ≥ 512×512           | ≥ 4000 px on the long edge          |
| Quantity          | ≥ 5 angles          | 60–120 photos (full angular sweep)  |
| Coverage          | Front + 3/4 + side  | 360° turntable + tilt sweeps        |
| Lighting          | Even ambient        | Diffuse softboxes, calibrated       |
| Backdrop          | Plain               | Colour-checker + plain backdrop     |

**Photogrammetry preparation**

- Use a colour checker in the first frame of each set.
- Capture alignment reference (stickers / fiducials) when feasible.
- Keep focal length and aperture constant within a sweep.

---

## 4. Text Corpus — High-Fidelity Tier

| Field            | Minimum (§4)          | High-fidelity                       |
| ---------------- | --------------------- | ----------------------------------- |
| Volume           | ≥ 10 000 characters   | 500 000+ characters                 |
| Time span        | Single point in time  | Years of correspondence             |
| Genres           | One                   | Multiple (formal / casual / technical / personal) |
| Metadata         | Minimal               | Per-message timestamps, channel, recipient role |
| De-identification| Per minimum standard  | Per minimum + topic-level review    |

---

## 5. 3D Assets — High-Fidelity Tier

| Field                | Minimum (§5)         | High-fidelity                       |
| -------------------- | -------------------- | ----------------------------------- |
| Format               | `vrm`/`glb`/`fbx`    | Layered: source `blend`/`ma`, exported `vrm` + `glb` |
| Mesh                 | Watertight           | Multi-LOD, retopologised            |
| Texture              | Base colour          | Full PBR set (BC/N/R/M/AO/SSS)      |
| Rigging              | Optional             | Full skeleton + facial bones        |
| Blendshapes          | Optional             | ARKit-52 + custom emotion blendshapes |
| Animation            | Static               | Idle, talk, gesture clips           |

---

## 6. Quality Assessment Rubrics

Use the following rubric in PR reviews and `derived/quality_report.json`:

| Dimension          | 1 (reject)              | 3 (acceptable)        | 5 (high-fidelity)             |
| ------------------ | ----------------------- | --------------------- | ----------------------------- |
| Audio SNR          | < 25 dB                 | 35–50 dB              | > 60 dB                       |
| Audio loudness     | clipped                 | -18 LUFS ±2 LU        | -18 LUFS ±0.5 LU              |
| Video resolution   | < 720p                  | 1080p                 | 4K+                           |
| Video stability    | shaky / cuts            | static head           | gimbal / tripod, multi-cam    |
| Lighting           | mixed colour            | even, no hard shadows | three-point, calibrated       |
| Image angle cover  | < 5 photos              | 5–15 photos           | 60+ photos / 360° sweep       |
| 3D mesh hygiene    | broken normals          | watertight            | retopologised, multi-LOD      |
| Consent depth      | text only               | text + signature      | text + signed video + ID-vp   |

A record's overall fidelity tier is the **minimum** dimension score. A
single low score (e.g. clipped audio) caps the overall tier.

---

## 7. High-Fidelity Pointer Examples

### Studio-quality voice master

```json
{
  "storage_uri": "s3://dlrs-private-vault/humans/.../voice_master_studio.wav",
  "checksum": "sha256:...",
  "region": "us-west-2",
  "format": "wav",
  "artifact_type": "audio",
  "sensitivity": "S3_BIOMETRIC",
  "access_policy": "private_runtime_only",
  "media_metadata": {
    "duration_seconds": 7200,
    "sample_rate_hz": 96000,
    "bit_depth": 24,
    "channels": 2,
    "loudness_lufs": -18.0,
    "true_peak_dbfs": -3.0,
    "codec": "pcm_s24le",
    "scenarios": ["read_neutral", "read_happy", "read_sad", "sustained_vowels", "numbers"]
  }
}
```

### 4K talking-head, multi-camera

```json
{
  "storage_uri": "s3://dlrs-private-vault/humans/.../talking_head_4k_multicam.mp4",
  "checksum": "sha256:...",
  "region": "us-west-2",
  "format": "mp4",
  "artifact_type": "video",
  "sensitivity": "S3_BIOMETRIC",
  "access_policy": "private_runtime_only",
  "media_metadata": {
    "duration_seconds": 1800,
    "width": 3840,
    "height": 2160,
    "fps": 60,
    "codec": "h265",
    "container": "mp4",
    "cameras": ["front", "3q_left", "3q_right"]
  }
}
```

### Photogrammetry sweep

```json
{
  "storage_uri": "s3://dlrs-private-vault/humans/.../photogrammetry_sweep.zip",
  "checksum": "sha256:...",
  "region": "us-west-2",
  "format": "zip",
  "artifact_type": "image",
  "sensitivity": "S3_BIOMETRIC",
  "access_policy": "private_runtime_only",
  "media_metadata": {
    "image_count": 96,
    "format": "dng",
    "long_edge_px": 6000,
    "color_chart_present": true
  }
}
```

---

## 8. When NOT to aim for high fidelity

- The subject only consents to text-persona use.
- The subject is a public figure and only public-data is being aggregated.
- The subject is deceased and only memorial-private use is intended.

In these cases, do not collect biometrics that exceed the lawful basis.
The minimum standard is sufficient.

---

## 9. Related documents

- [`docs/COLLECTION_STANDARD.md`](./COLLECTION_STANDARD.md)
- [`docs/OBJECT_STORAGE_POINTERS.md`](./OBJECT_STORAGE_POINTERS.md)
- [`policies/watermarking-and-disclosure.md`](../policies/watermarking-and-disclosure.md)
- [`policies/acceptable-use.md`](../policies/acceptable-use.md)
