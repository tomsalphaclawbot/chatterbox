#!/usr/bin/env bash
set -euo pipefail

cd /Users/openclaw/.openclaw/workspace/projects/chatterbox
source .venv/bin/activate

export CHATTERBOX_DEVICE="${CHATTERBOX_DEVICE:-mps}"
export VOICE_S3_ENDPOINT="${VOICE_S3_ENDPOINT:-http://127.0.0.1:9000}"
export VOICE_S3_ACCESS_KEY_ID="${VOICE_S3_ACCESS_KEY_ID:-minioadmin}"
export VOICE_S3_SECRET_ACCESS_KEY="${VOICE_S3_SECRET_ACCESS_KEY:-minioadmin}"
export VOICE_S3_BUCKET="${VOICE_S3_BUCKET:-resonance-audio}"

exec uvicorn api_server:app --host 127.0.0.1 --port 8000
