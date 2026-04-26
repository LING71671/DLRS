#!/usr/bin/env bash
# End-to-end DLRS v0.6 memory-graph walkthrough.
#
# Runs text cleaning -> memory_atoms -> knowledge_graph against a small
# fictional diary excerpt. Every step uses the deterministic,
# dependency-free backend (regex tokenizer, paragraph atomiser, regex
# entity extractor) so the demo runs offline on a vanilla VM. The
# descriptor->audit bridge (#58) writes one derived_asset_emitted event
# per pipeline into audit/events.jsonl.
#
# To swap to the optional spaCy backend for memory_atoms, set
# REAL_ATOMS=1; spaCy must be installed separately
# (see docs/PIPELINE_GUIDE.md).
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# REPO_ROOT defaults to the parent-of-parent of this script (works for the
# in-repo example). Tests that copy the demo to a tmp directory override
# DLRS_REPO_ROOT so run_pipeline.py is still found.
REPO_ROOT="${DLRS_REPO_ROOT:-$(cd "${DEMO_DIR}/../.." && pwd)}"
RUN="python ${REPO_ROOT}/tools/run_pipeline.py"

ATOMS_BACKEND="${REAL_ATOMS:+spacy}"
ATOMS_BACKEND="${ATOMS_BACKEND:-paragraph}"

cd "${DEMO_DIR}"

# 0. Stage the fictional diary text. DLRS is pointer-first so the corpus
# is NOT committed to git; we regenerate it deterministically on every
# run. The checksum in manifest.json is fixed against this content.
mkdir -p artifacts/raw/text
cat > artifacts/raw/text/diary.txt <<'TXT'
On Tuesday, Alice met Bob at the Beijing campus to plan the autumn product launch.

European Commission representatives joined the call midway through, pressing on the data-residency clause. Alice agreed to circulate a draft term sheet by end of week.

Charlie followed up the next morning with a one-page memo summarising the action items, copying David and the rest of the working group.
TXT

# 1. Text cleaning - normalise + redact the diary into derived/text/diary.clean.txt.
echo "[1/3] text cleaning"
$RUN text \
  --record "${DEMO_DIR}" \
  --input "artifacts/raw/text/diary.txt" \
  --mode both

# 2. Memory atoms - paragraph atomiser by default; spaCy on REAL_ATOMS=1.
echo "[2/3] memory_atoms (${ATOMS_BACKEND})"
$RUN memory_atoms \
  --record "${DEMO_DIR}" \
  --backend "${ATOMS_BACKEND}" \
  --sensitivity "S1_INTERNAL"

# 3. Knowledge graph - regex entity + co-mention edge extraction.
echo "[3/3] knowledge_graph"
$RUN knowledge_graph \
  --record "${DEMO_DIR}" \
  --sensitivity "S1_INTERNAL"

echo
echo "Demo complete. Generated artefacts:"
find "${DEMO_DIR}/derived" -maxdepth 3 -type f | sort | sed "s|${DEMO_DIR}/||"

echo
echo "Audit log (one derived_asset_emitted event per descriptor):"
if [[ -f "${DEMO_DIR}/audit/events.jsonl" ]]; then
  python - <<PY
import json
from pathlib import Path
events = Path("${DEMO_DIR}/audit/events.jsonl").read_text(encoding="utf-8").splitlines()
for i, line in enumerate(events, start=1):
    if not line.strip():
        continue
    e = json.loads(line)
    md = e.get("metadata") or {}
    print(f"  L{i}: {e['event_type']} pipeline={md.get('pipeline')!r} prev_hash={'(genesis)' if e.get('prev_hash') is None else e['prev_hash'][:12]+'...'}")
PY
else
  echo "  (no audit log; run_demo.sh did not exercise the bridge)"
fi
