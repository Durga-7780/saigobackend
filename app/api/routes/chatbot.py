"""
Chatbot Routes
AI-powered employee assistance
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, List

from app.models.employee import Employee
from app.api.routes.auth import get_current_employee
from app.ai.chatbot import chatbot_service
from app.services.voicebot import voicebot_service


router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request"""
    query: str
    context: Optional[Dict] = None


class ChatResponse(BaseModel):
    """Chat response"""
    answer: str
    source: str
    suggestions: list


class VoiceSessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str


class VoiceSessionsListResponse(BaseModel):
    sessions: List[VoiceSessionResponse]


@router.post("/ask", response_model=ChatResponse)
async def ask_chatbot(
    request: ChatRequest,
    current_employee: Employee = Depends(get_current_employee)
):
    """
    Ask the AI chatbot a question
    """
    try:
        context = request.context or {}
        
        # If Admin is asking for reports, inject collective stats
        if context.get("type") == "admin_reports" and current_employee.role in ["admin", "hr"]:
            from app.api.routes.dashboard import get_admin_stats
            admin_stats = await get_admin_stats(current_employee)
            context["all_stats"] = admin_stats
            
        response = await chatbot_service.get_response(
            query=request.query,
            employee_id=current_employee.employee_id,
            context=context
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chatbot error: {str(e)}"
        )


@router.get("/suggestions")
async def get_suggestions():
    """
    Get common query suggestions
    """
    return {
        "suggestions": [
            "How do I apply for leave?",
            "Show my attendance for this month",
            "What is my leave balance?",
            "How to mark attendance?",
            "When is the next holiday?",
            "What is the work from home policy?",
            "How do I update my profile?",
            "When is salary day?",
            "What are the working hours?"
        ]
    }


@router.post("/voice/sessions")
async def create_voice_session(
    current_employee: Employee = Depends(get_current_employee)
):
    session = await voicebot_service.create_session(current_employee.employee_id)
    return {
        "session_id": str(session.id),
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


@router.get("/voice/sessions", response_model=VoiceSessionsListResponse)
async def list_voice_sessions(
    current_employee: Employee = Depends(get_current_employee)
):
    sessions = await voicebot_service.list_sessions(current_employee.employee_id)
    return {
        "sessions": [
            {
                "session_id": str(s.id),
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ]
    }


@router.get("/voice/sessions/{session_id}")
async def get_voice_session(
    session_id: str,
    current_employee: Employee = Depends(get_current_employee)
):
    session = await voicebot_service.get_session(current_employee.employee_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Voice session not found")

    return {
        "session_id": str(session.id),
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "messages": [
            {
                "role": m.role,
                "text": m.text,
                "created_at": m.created_at.isoformat(),
            }
            for m in session.messages
        ],
    }


@router.post("/voice/turn")
async def voice_turn(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    current_employee: Employee = Depends(get_current_employee),
):
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Audio file is empty")

        result = await voicebot_service.process_turn(
            employee_id=current_employee.employee_id,
            session_id=session_id,
            audio_filename=audio.filename or "voice.webm",
            audio_bytes=audio_bytes,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voicebot error: {str(e)}")


@router.post("/voice/idle-greeting")
async def voice_idle_greeting(
    session_id: str = Form(...),
    current_employee: Employee = Depends(get_current_employee),
):
    try:
        result = await voicebot_service.idle_greeting(
            employee_id=current_employee.employee_id,
            session_id=session_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voicebot error: {str(e)}")
