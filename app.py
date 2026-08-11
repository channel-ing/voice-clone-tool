import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="声音克隆工具")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY  = os.getenv("MINIMAX_API_KEY", "")
GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "")
BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.chat/v1")


def _params() -> dict:
    return {"GroupId": GROUP_ID} if GROUP_ID else {}


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {API_KEY}"}


@app.get("/")
async def root():
    return FileResponse("index.html")


@app.post("/api/clone")
async def clone_voice(file: UploadFile = File(...)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="服务器未配置 MINIMAX_API_KEY")
    content = await file.read()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{BASE_URL}/voice_clone",
            headers=_auth_headers(),
            files={"file": (file.filename, content, file.content_type or "audio/mpeg")},
            params=_params(),
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    result = resp.json()
    base = result.get("base_resp", {})
    if base.get("status_code", -1) != 0:
        raise HTTPException(status_code=400, detail=base.get("status_msg", "MiniMax 返回错误"))
    return result


@app.post("/api/tts")
async def text_to_speech(payload: dict = Body(...)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="服务器未配置 MINIMAX_API_KEY")
    voice_id = (payload.get("voice_id") or "").strip()
    text     = (payload.get("text") or "").strip()
    speed    = float(payload.get("speed", 1.0))
    pitch    = int(payload.get("pitch", 0))
    if not voice_id:
        raise HTTPException(status_code=400, detail="voice_id 不能为空")
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空")
    body = {
        "model": "speech-02-hd",
        "text": text,
        "stream": False,
        "voice_setting": {"voice_id": voice_id, "speed": speed, "vol": 1.0, "pitch": pitch},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3"},
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{BASE_URL}/t2a_v2",
            headers={**_auth_headers(), "Content-Type": "application/json"},
            params=_params(),
            json=body,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    result = resp.json()
    base = result.get("base_resp", {})
    if base.get("status_code", -1) != 0:
        raise HTTPException(status_code=400, detail=base.get("status_msg", "MiniMax 返回错误"))
    return result
