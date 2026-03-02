import io
import os
import tempfile
from pathlib import Path
from threading import Lock
from typing import Optional

import torch
import torchaudio as ta
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

try:
    import boto3  # optional, only needed for S3/MinIO voice_key resolution
except Exception:  # pragma: no cover
    boto3 = None

from chatterbox.tts_turbo import ChatterboxTurboTTS


class TTSRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    voice_key: str = Field(..., min_length=1, max_length=1024)
    temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: int = Field(default=1000, ge=1, le=10000)
    repetition_penalty: float = Field(default=1.2, ge=1.0, le=2.0)
    norm_loudness: bool = Field(default=True)


app = FastAPI(title="Chatterbox Local API", version="0.1.1")

_model = None
_model_lock = Lock()


def _pick_device() -> str:
    forced = os.getenv("CHATTERBOX_DEVICE", "").strip().lower()
    if forced:
        return forced

    if torch.cuda.is_available():
        return "cuda"

    mps_ok = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    if mps_ok:
        return "mps"

    return "cpu"


def _get_model():
    global _model
    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        device = _pick_device()
        _model = ChatterboxTurboTTS.from_pretrained(device=device)
        return _model


def _s3_client_if_configured():
    if boto3 is None:
        return None

    endpoint = os.getenv("VOICE_S3_ENDPOINT", "").strip()
    access_key = os.getenv("VOICE_S3_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("VOICE_S3_SECRET_ACCESS_KEY", "").strip()

    if not (endpoint and access_key and secret_key):
        return None

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=os.getenv("VOICE_S3_REGION", "us-east-1"),
    )


def _resolve_voice_path(voice_key: str) -> tuple[str, Optional[str]]:
    p = Path(voice_key)
    if p.exists():
        return str(p.resolve()), None

    root = os.getenv("VOICE_ROOT", "").strip()
    if root:
        rooted = Path(root) / voice_key
        if rooted.exists():
            return str(rooted.resolve()), None

    bucket = os.getenv("VOICE_S3_BUCKET", "").strip()
    s3 = _s3_client_if_configured()
    if bucket and s3 is not None:
        tmp = tempfile.NamedTemporaryFile(prefix="voice-", suffix=".wav", delete=False)
        tmp.close()
        try:
            s3.download_file(bucket, voice_key, tmp.name)
            return tmp.name, tmp.name
        except Exception as e:
            Path(tmp.name).unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"Failed to load voice_key from S3/MinIO: {e}")

    raise HTTPException(
        status_code=400,
        detail=(
            f"Voice prompt not found for voice_key='{voice_key}'. "
            "Provide an absolute/local path, set VOICE_ROOT, or configure VOICE_S3_* env vars."
        ),
    )


@app.get("/")
def root():
    return {
        "service": "chatterbox-local-api",
        "ok": True,
        "version": "0.1.1",
        "endpoints": {
            "health": "/health",
            "generate": "/generate",
            "docs": "/docs",
        },
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "model_loaded": _model is not None,
        "device": _pick_device(),
    }


@app.post("/generate")
def generate(req: TTSRequest):
    model = _get_model()
    resolved_voice_path, temp_file = _resolve_voice_path(req.voice_key)

    try:
        wav = model.generate(
            req.prompt,
            audio_prompt_path=resolved_voice_path,
            temperature=req.temperature,
            top_p=req.top_p,
            top_k=req.top_k,
            repetition_penalty=req.repetition_penalty,
            norm_loudness=req.norm_loudness,
        )

        buf = io.BytesIO()
        ta.save(buf, wav, model.sr, format="wav")
        buf.seek(0)
        return StreamingResponse(buf, media_type="audio/wav")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")
    finally:
        if temp_file:
            Path(temp_file).unlink(missing_ok=True)
