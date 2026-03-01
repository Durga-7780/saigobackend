"""
Voicebot service
Uses Groq STT + LangChain(ChatGroq) + Groq TTS and stores conversation history.
"""
from __future__ import annotations

import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from openai import AsyncOpenAI

from app.config import settings
from app.models.voicebot import VoiceConversation, VoiceMessage


class VoicebotService:
    def __init__(self):
        self.groq_client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        self.llm = ChatGroq(
            model=settings.GROQ_MODEL,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0.3,
        )

    async def create_session(self, employee_id: str) -> VoiceConversation:
        conversation = VoiceConversation(employee_id=employee_id, messages=[])
        await conversation.insert()
        return conversation

    async def list_sessions(self, employee_id: str, limit: int = 20) -> List[VoiceConversation]:
        return await VoiceConversation.find(
            VoiceConversation.employee_id == employee_id
        ).sort("-updated_at").limit(limit).to_list()

    async def get_session(self, employee_id: str, session_id: str) -> Optional[VoiceConversation]:
        session = await VoiceConversation.get(session_id)
        if not session or session.employee_id != employee_id:
            return None
        return session

    async def transcribe_audio(self, filename: str, audio_bytes: bytes) -> str:
        transcript = await self.groq_client.audio.transcriptions.create(
            model=settings.GROQ_STT_MODEL,
            file=(filename, audio_bytes),
        )
        text = (getattr(transcript, "text", None) or "").strip()
        return text

    async def synthesize_speech_base64(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Convert text to speech using Groq's Orpheus TTS model
        Returns base64-encoded audio and format, or None if TTS fails
        """
        try:
            speech_response = await self.groq_client.audio.speech.create(
                model=settings.GROQ_TTS_MODEL,
                voice=settings.GROQ_TTS_VOICE,
                input=text,
                response_format="wav",
            )

            # Read the audio content from response
            if hasattr(speech_response, 'content'):
                audio_bytes = speech_response.content
            elif hasattr(speech_response, 'read'):
                audio_bytes = await speech_response.read() if hasattr(speech_response.read(), '__await__') else speech_response.read()
            else:
                audio_bytes = bytes(speech_response)

            if audio_bytes:
                return base64.b64encode(audio_bytes).decode("utf-8"), "wav"
            return None
        except Exception as e:
            print(f"Groq TTS Error: {str(e)}")
            # Fallback to browser SpeechSynthesis API
            return None

    def _build_messages(self, history: List[VoiceMessage], user_text: str):
        system = SystemMessage(
            content=(
                "You are Saigo Voice Assistant for Attendance Pro portal. "
                "You are strictly a portal assistant. "
                "Allowed scope: attendance, leaves, salary/payslips, profile, documents, meal booking, "
                "portal features, and HR policies in this portal. "
                "If user asks anything outside portal scope, reply exactly: "
                "'I am designed to assist only with Attendance Pro portal-related information.' "
                "Keep answers brief, practical, and easy to speak."
            )
        )
        messages = [system]
        for item in history[-12:]:
            if item.role == "user":
                messages.append(HumanMessage(content=item.text))
            else:
                messages.append(AIMessage(content=item.text))
        messages.append(HumanMessage(content=user_text))
        return messages

    async def generate_reply(self, history: List[VoiceMessage], user_text: str) -> str:
        messages = self._build_messages(history, user_text)
        response = await self.llm.ainvoke(messages)
        return (response.content or "").strip()

    async def process_turn(
        self,
        employee_id: str,
        session_id: str,
        audio_filename: str,
        audio_bytes: bytes,
    ) -> Dict:
        session = await self.get_session(employee_id=employee_id, session_id=session_id)
        if not session:
            raise ValueError("Voice session not found")

        user_text = await self.transcribe_audio(audio_filename, audio_bytes)
        if not user_text:
            raise ValueError("Could not transcribe audio")

        assistant_text = await self.generate_reply(session.messages, user_text)
        if not assistant_text:
            assistant_text = "I could not generate a response. Please try again."

        session.messages.append(VoiceMessage(role="user", text=user_text))
        session.messages.append(VoiceMessage(role="assistant", text=assistant_text))
        session.last_user_text = user_text
        session.updated_at = datetime.utcnow()
        await session.save()

        tts_result = await self.synthesize_speech_base64(assistant_text)
        audio_base64 = tts_result[0] if tts_result else None
        audio_format = tts_result[1] if tts_result else None

        return {
            "session_id": str(session.id),
            "user_text": user_text,
            "assistant_text": assistant_text,
            "assistant_audio_base64": audio_base64,
            "assistant_audio_format": audio_format,
            "messages": [
                {
                    "role": m.role,
                    "text": m.text,
                    "created_at": m.created_at.isoformat(),
                }
                for m in session.messages
            ],
        }

    async def idle_greeting(self, employee_id: str, session_id: str) -> Dict:
        session = await self.get_session(employee_id=employee_id, session_id=session_id)
        if not session:
            raise ValueError("Voice session not found")

        greeting_text = "Hi there. Anything you want to know about the portal, like attendance, leave, or salary?"
        session.messages.append(VoiceMessage(role="assistant", text=greeting_text))
        session.updated_at = datetime.utcnow()
        await session.save()

        tts_result = await self.synthesize_speech_base64(greeting_text)
        audio_base64 = tts_result[0] if tts_result else None
        audio_format = tts_result[1] if tts_result else None
        return {
            "session_id": str(session.id),
            "assistant_text": greeting_text,
            "assistant_audio_base64": audio_base64,
            "assistant_audio_format": audio_format,
            "messages": [
                {
                    "role": m.role,
                    "text": m.text,
                    "created_at": m.created_at.isoformat(),
                }
                for m in session.messages
            ],
        }


voicebot_service = VoicebotService()
