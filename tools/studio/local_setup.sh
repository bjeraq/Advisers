#!/usr/bin/env bash
# تجهيز المونتاج على جهاز الجلسة نفسه بدل ساندبوكس هيغزفيلد (قاعدة local_editing).
# الاستخدام:  bash tools/studio/local_setup.sh <slug>
# ينشئ ~/studio-venv (Pillow مع raqm + faster-whisper)، ينزّل نموذج التفريغ مرة وحدة،
# ويجهز مجلد شغل ~/majlis_local فيه tools/ و fonts/ و episodes/<slug>/ و src/.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SLUG="${1:-}"
VENV="$HOME/studio-venv"
W="$HOME/majlis_local"
export HF_HUB_DISABLE_XET=1   # نموذج التفريغ ينزل من us.aws.cdn.hf.co (مسموح بالشبكة)

command -v ffmpeg >/dev/null && command -v montage >/dev/null || { echo "ffmpeg/ImageMagick ناقصين"; exit 1; }
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q "Pillow>=10.4" faster-whisper
fi
"$VENV/bin/python" - <<'EOF'
from PIL import features
assert features.check('raqm'), 'Pillow بدون raqm — الكتابة العربية بتنقلب'
from faster_whisper import WhisperModel
WhisperModel('small', device='cpu', compute_type='int8')
print('venv ok: raqm + whisper small')
EOF

mkdir -p "$W/src/lines" "$W/episodes" "$W/chk"
ln -sfn "$REPO/tools" "$W/tools"
ln -sfn "$REPO/tools/studio/fonts" "$W/fonts"
if [ -n "$SLUG" ]; then
  mkdir -p "$W/episodes/$SLUG"
  cp "$REPO/tools/studio/episodes/$SLUG/episode.json" "$W/episodes/$SLUG/episode.json"
fi
echo "جاهز: cd $W && HF_HUB_DISABLE_XET=1 $VENV/bin/python tools/studio/build.py episodes/<slug>/episode.json --res 720 --stage draft"
