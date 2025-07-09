# main.py
import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

MODEL = "models/gemini-2.5-flash-preview-native-audio-dialog"

CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
)

@app.get("/")
def root():
    return {"message": "Gemini STS backend is live!"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔌 Client connected")

    async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
        receive_task = asyncio.create_task(session_receiver(session, websocket))

        try:
            while True:
                audio = await websocket.receive_bytes()
                # ✅ Use the newer method for streaming audio
                await session.send_realtime_input(
                    input=types.PartialAudio(data=audio, mime_type="audio/pcm")
                )
        except WebSocketDisconnect:
            print("❌ Client disconnected")
            receive_task.cancel()

async def session_receiver(session, websocket):
    async for turn in session.receive():
        async for response in turn:
            if response.data:
                await websocket.send_bytes(response.data)
            if response.text:
                print("🗣️ Gemini:", response.text)

