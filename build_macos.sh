#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name TimeLogTracker \
  main.py

echo "Build finished: dist/TimeLogTracker"
