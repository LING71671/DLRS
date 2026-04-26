#!/usr/bin/env bash
# Reference build wrapper for the minimal-life-package example.
#
# Walks the v0.1 .life builder against the source DLRS record subset
# committed in this directory and writes a .life zip to ./out/.
#
# Re-running on the same source record will append a new
# `package_emitted` event to audit/events.jsonl on every invocation
# (the audit chain is append-only). For deterministic builds (e.g.
# the test driver), set `DLRS_LIFE_DETERMINISTIC=1` so the
# package_id, timestamps, and audit event_id are pinned. Pinned mode
# still appends one event per build, so re-runs require resetting the
# audit log via git checkout (see tools/test_minimal_life_package.py
# for the pattern).
#
# See docs/LIFE_FILE_STANDARD.md for the file-format spec, and
# docs/LIFE_RUNTIME_STANDARD.md for what a compatible runtime is
# expected to do with the resulting .life.

set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${DLRS_REPO_ROOT:-$(cd "${DEMO_DIR}/../.." && pwd)}"

OUT_DIR="${DEMO_DIR}/out"
mkdir -p "${OUT_DIR}"

python "${REPO_ROOT}/tools/build_life_package.py" \
  --record "${DEMO_DIR}" \
  --output-dir "${OUT_DIR}" \
  --mode pointer \
  --issuer-role self \
  --issuer-identifier "example-self" \
  --signature-ref "consent/consent.md" \
  --consent-evidence-ref "consent/consent.md" \
  --verification-level self_attested \
  --withdrawal-endpoint "https://example.org/dlrs/withdraw/EXAMPLE_minimal_life" \
  --runtime-compatibility "dlrs-runtime-v0" \
  --ai-disclosure visible_label_required \
  --forbidden-uses \
      impersonation_for_fraud \
      political_endorsement \
      explicit_content \
      voice_clone_for_fraud \
      avatar_clone \
      memorial_reanimation_without_executor \
  --lifetime-days 365 \
  "$@"
