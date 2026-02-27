"""
Voicebot conversation models
Stores per-user voice conversation history.
"""
from datetime import datetime
from typing import List, Optional, Literal

from beanie import Document
from pydantic import BaseModel, Field


class VoiceMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VoiceConversation(Document):
    employee_id: str
    title: str = "Voice Session"
    messages: List[VoiceMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_user_text: Optional[str] = None

    class Settings:
        name = "voice_conversations"
        indexes = ["employee_id", "created_at", "updated_at"]
