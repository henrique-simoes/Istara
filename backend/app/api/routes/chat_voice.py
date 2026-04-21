from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter()

class VoiceTranscribeRequest(BaseModel):
    project_id: str
    dummy: bool = False

@router.post("/chat/voice-transcribe")
async def voice_transcribe(request: VoiceTranscribeRequest):
    """Voice transcription endpoint (Phase Alpha)."""
    if request.dummy:
        return {"status": "success", "text": "Mock transcription"}
    return {"status": "error", "message": "No audio file provided"}
