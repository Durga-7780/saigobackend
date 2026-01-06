"""
Chatbot Routes
AI-powered employee assistance
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict

from app.models.employee import Employee
from app.api.routes.auth import get_current_employee
from app.ai.chatbot import chatbot_service


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
