#!/usr/bin/env bash
set -euo pipefail
# Modelele sunt descărcate la CONSTRUIREA aplicației, NU de aplicația instalată.
# Versiune fixată la tag-ul 4.0.0 pentru reproductibilitatea OCR.
# Poți modifica lista după verificarea licenței și a mărimii APK.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/app/src/main/assets/tessdata"
mkdir -p "$DEST"
for lang in ron eng; do
  echo "Bundling offline OCR model: $lang"
  curl --fail --location --retry 3 --silent --show-error \
    "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.0.0/${lang}.traineddata" \
    --output "$DEST/${lang}.traineddata"
  test "$(wc -c < "$DEST/${lang}.traineddata")" -gt 100000
done
