#!/usr/bin/env bash
set -euo pipefail

cd /Users/openclaw/.openclaw/workspace/projects/chatterbox
source .venv/bin/activate

export PYTHONUNBUFFERED=1

exec python gradio_tts_turbo_app.py
