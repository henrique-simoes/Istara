from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_project_access
from app.models.database import get_db

router = APIRouter()

class VoiceTranscribeRequest(BaseModel):
    project_id: str
    dummy: bool = False

@router.post("/chat/voice-transcribe")
async def voice_transcribe(
    data: VoiceTranscribeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Voice transcription endpoint (Phase Alpha)."""
    await require_project_access(db, request, data.project_id, min_role="researcher")
    if data.dummy:
        return {"status": "success", "text": "Mock transcription"}
    return {"status": "error", "message": "No audio file provided"}
