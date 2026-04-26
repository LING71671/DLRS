#!/usr/bin/env bash
# End-to-end DLRS v0.5 pipeline walkthrough.
#
# Runs ASR -> text cleaning -> embedding -> moderation against the demo
# record. Every step uses the deterministic, dependency-free backend
# (dummy ASR, hash embedder) so the demo runs offline on a vanilla VM.
#
# To swap to the real backends after exercising the offline path, set
# REAL_ASR=1 (faster-whisper) and/or REAL_EMBED=1 (sentence-transformers).
# Both must be installed separately; see docs/PIPELINE_GUIDE.md.

set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# REPO_ROOT defaults to the parent-of-parent of this script (works for the
# in-repo example). Tests that copy the demo to a tmp directory override
# DLRS_REPO_ROOT so run_pipeline.py is still found.
REPO_ROOT="${DLRS_REPO_ROOT:-$(cd "${DEMO_DIR}/../.." && pwd)}"
RUN="python ${REPO_ROOT}/tools/run_pipeline.py"

ASR_BACKEND="${REAL_ASR:+faster-whisper}"
ASR_BACKEND="${ASR_BACKEND:-dummy}"
EMBED_BACKEND="${REAL_EMBED:+sentence-transformers}"
EMBED_BACKEND="${EMBED_BACKEND:-hash}"

cd "${DEMO_DIR}"

# 0. Ensure the placeholder WAV exists. DLRS is pointer-first so the audio
# is NOT committed to git; we regenerate it deterministically on every run
# (0.3 s of silence at 16 kHz / mono / 16-bit). The checksum in
# manifest.json is fixed against this generator output.
mkdir -p artifacts/raw/audio
python - <<'PY'
import wave, struct
out = "artifacts/raw/audio/voice_demo.wav"
sr, secs = 16000, 0.3
with wave.open(out, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(struct.pack("<" + "h" * int(sr * secs), *([0] * int(sr * secs))))
PY

# 1. ASR — transcribe the placeholder WAV into derived/asr/voice_demo.transcript.json.
echo "[1/4] ASR ($ASR_BACKEND)"
$RUN asr --record "${DEMO_DIR}" --backend "$ASR_BACKEND"

# 2. Text cleaning — normalise + redact the transcript into derived/text/.
echo "[2/4] text cleaning"
$RUN text \
  --record "${DEMO_DIR}" \
  --input "derived/asr/voice_demo.transcript.json" \
  --mode both

# 3. Vectorization — chunk + embed clean text into derived/vectorization/.
echo "[3/4] vectorization ($EMBED_BACKEND)"
$RUN vectorization --record "${DEMO_DIR}" --backend "$EMBED_BACKEND"

# 4. Moderation — scan clean text into derived/moderation/.
echo "[4/4] moderation"
$RUN moderation --record "${DEMO_DIR}"

echo
echo "Demo complete. Generated artefacts:"
find "${DEMO_DIR}/derived" -maxdepth 3 -type f | sort | sed "s|${DEMO_DIR}/||"
