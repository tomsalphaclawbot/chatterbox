# Chatterbox Local API (for Resonance self-host)

This wrapper exposes a Resonance-compatible `/generate` endpoint backed by local Chatterbox-Turbo.

## 1) Setup

```bash
cd projects/chatterbox
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
pip install -r requirements-api.txt
```

## 2) Start API

```bash
source .venv/bin/activate
export CHATTERBOX_DEVICE=mps   # macOS Apple Silicon (or cpu/cuda)
# Optional: local folder lookup for voice_key
export VOICE_ROOT=/absolute/path/to/voice/files
# Optional: MinIO/S3 lookup for voice_key
# export VOICE_S3_ENDPOINT=http://127.0.0.1:9000
# export VOICE_S3_ACCESS_KEY_ID=minioadmin
# export VOICE_S3_SECRET_ACCESS_KEY=minioadmin
# export VOICE_S3_BUCKET=resonance-audio

uvicorn api_server:app --host 0.0.0.0 --port 8000
```

## 3) Smoke tests

```bash
curl -s http://127.0.0.1:8000/health
```

Generation test (with local voice prompt file):

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"Hello from local Chatterbox.",
    "voice_key":"/absolute/path/to/10s_reference.wav"
  }' \
  --output /tmp/chatterbox-test.wav
```

## 4) Resonance integration target

When running Resonance in Docker and this API on host:

- `CHATTERBOX_API_URL=http://host.docker.internal:8000`

If/when MinIO is enabled and voices are stored as object keys, set `VOICE_S3_*` vars on this API service so `voice_key` resolves from object storage.
