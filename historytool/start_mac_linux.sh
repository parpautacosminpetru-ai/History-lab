#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo '[historytool] Creez un mediu Python local și instalez dependențele…'
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
printf '\n[historytool] Deschide http://127.0.0.1:8765 dacă browserul nu pornește automat.\n'
.venv/bin/python app.py
