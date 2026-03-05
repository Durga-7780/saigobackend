"""
Voicebot service
Uses Groq STT + LangChain(ChatGroq) + XTTS TTS and stores conversation history.
"""
from __future__ import annotations

import base64
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import asyncio

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from openai import AsyncOpenAI

from app.config import settings
from app.models.voicebot import VoiceConversation, VoiceMessage

# Initialize XTTS TTS model (lazy loaded)
_xtts_model = None
_executor = ThreadPoolExecutor(max_workers=2)


def _get_xtts_model():
    """Load XTTS model (singleton pattern)"""
    global _xtts_model
    if _xtts_model is None:
        try:
            from TTS.api import TTS
            xtts_gpu_enabled = bool(getattr(settings, "XTTS_GPU_ENABLED", False))
            xtts_model_name = getattr(settings, "XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
            device = "cuda" if xtts_gpu_enabled else "cpu"
            _xtts_model = TTS(model_name=xtts_model_name, gpu=xtts_gpu_enabled, progress_bar=False)
            print(f"✅ XTTS model loaded on {device}")
        except Exception as e:
            print(f"❌ Failed to load XTTS model: {str(e)}")
            _xtts_model = False
    return _xtts_model if _xtts_model else None


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
        """Transcribe audio using Groq Whisper STT"""
        transcript = await self.groq_client.audio.transcriptions.create(
            model=settings.GROQ_STT_MODEL,
            file=(filename, audio_bytes),
        )
        text = (getattr(transcript, "text", None) or "").strip()
        return text

    async def _synthesize_xtts(self, text: str) -> Optional[bytes]:
        """Synthesize speech using XTTS model (runs in thread pool)"""
        try:
            tts_model = _get_xtts_model()
            if not tts_model:
                return None

            # Run TTS in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            def generate_audio():
                try:
                    xtts_language = getattr(settings, "XTTS_LANGUAGE", "en")
                    xtts_gpu_enabled = bool(getattr(settings, "XTTS_GPU_ENABLED", False))
                    tts_model.tts_to_file(
                        text=text,
                        file_path=tmp_path,
                        language=xtts_language,
                        gpu=xtts_gpu_enabled,
                    )
                    with open(tmp_path, 'rb') as f:
                        audio_bytes = f.read()
                    os.unlink(tmp_path)
                    print(f"✅ XTTS generated audio ({len(audio_bytes)} bytes)")
                    return audio_bytes
                except Exception as e:
                    print(f"❌ XTTS generation error: {str(e)}")
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    return None

            audio_bytes = await loop.run_in_executor(_executor, generate_audio)
            return audio_bytes

        except Exception as e:
            print(f"❌ XTTS Error: {str(e)}")
            return None

    async def _synthesize_groq(self, text: str) -> Optional[bytes]:
        """Synthesize speech using Groq TTS (fallback)"""
        try:
            groq_tts_model = getattr(settings, "GROQ_TTS_MODEL", "playai-tts")
            groq_tts_voice = getattr(settings, "GROQ_TTS_VOICE", "hannah")
            speech_response = await self.groq_client.audio.speech.create(
                model=groq_tts_model,
                voice=groq_tts_voice,
                input=text,
                response_format="wav",
            )

            if hasattr(speech_response, 'content'):
                return speech_response.content
            elif hasattr(speech_response, "read"):
                content = speech_response.read()
                if hasattr(content, "__await__"):
                    return await content
                return content
            else:
                return bytes(speech_response)

        except Exception as e:
            print(f"❌ Groq TTS Error: {str(e)}")
            return None

    async def synthesize_speech_base64(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Convert text to speech using XTTS (primary) or Groq (fallback)
        Returns base64-encoded audio and format, or None if TTS fails
        """
        audio_bytes = None

        # Try XTTS first if enabled
        tts_engine = str(getattr(settings, "TTS_ENGINE", "groq")).lower()
        xtts_language = getattr(settings, "XTTS_LANGUAGE", "en")

        if tts_engine == "xtts":
            print(f"🎵 Using XTTS TTS (Language: {xtts_language})")
            audio_bytes = await self._synthesize_xtts(text)

        # Fallback to Groq if XTTS fails or not enabled
        if not audio_bytes:
            print(f"🎵 Using Groq TTS (Fallback)")
            audio_bytes = await self._synthesize_groq(text)

        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("utf-8"), "wav"

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
        """Generate AI response using ChatGroq LLM"""
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
        """Process a complete voice conversation turn"""
        session = await self.get_session(employee_id=employee_id, session_id=session_id)
        if not session:
            raise ValueError("Voice session not found")

        # Step 1: Transcribe user audio
        user_text = await self.transcribe_audio(audio_filename, audio_bytes)
        if not user_text:
            raise ValueError("Could not transcribe audio")

        # Step 2: Generate AI response
        assistant_text = await self.generate_reply(session.messages, user_text)
        if not assistant_text:
            assistant_text = "I could not generate a response. Please try again."

        # Step 3: Synthesize response to audio
        tts_result = await self.synthesize_speech_base64(assistant_text)
        audio_base64 = tts_result[0] if tts_result else None
        audio_format = tts_result[1] if tts_result else None

        # Step 4: Save to database
        session.messages.append(VoiceMessage(role="user", text=user_text))
        session.messages.append(VoiceMessage(role="assistant", text=assistant_text))
        session.last_user_text = user_text
        session.updated_at = datetime.utcnow()
        await session.save()

        return {
            "session_id": str(session.id),
            "user_text": user_text,
            "assistant_text": assistant_text,
            "assistant_audio_base64": audio_base64,
            "assistant_audio_format": audio_format,
            "tts_available": bool(audio_base64),
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
        """Generate greeting when user is idle"""
        session = await self.get_session(employee_id=employee_id, session_id=session_id)
        if not session:
            raise ValueError("Voice session not found")

        greeting_text = "Hi there. Anything you want to know about the portal, like attendance, leave, or salary?"

        # Synthesize greeting to audio
        tts_result = await self.synthesize_speech_base64(greeting_text)
        audio_base64 = tts_result[0] if tts_result else None
        audio_format = tts_result[1] if tts_result else None

        # Save greeting to session
        session.messages.append(VoiceMessage(role="assistant", text=greeting_text))
        session.updated_at = datetime.utcnow()
        await session.save()

        return {
            "session_id": str(session.id),
            "assistant_text": greeting_text,
            "assistant_audio_base64": audio_base64,
            "assistant_audio_format": audio_format,
            "tts_available": bool(audio_base64),
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
