"""
Chatbot routes
- POST /chat - Chat with CloudSense AI
- POST /chat/clear - Clear conversation history
- POST /chat/summarize/{id} - Summarize analysis
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core import get_current_user, get_analysis, get_analysis_results
from modules.chatbot import chatbot

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    include_analysis_context: bool = False
    analysis_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_length: int


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Chat with CloudSense AI assistant.
    
    The assistant specializes in:
    - Tropical Cloud Cluster analysis
    - Satellite data interpretation
    - Weather patterns and cyclone formation
    """
    context = None
    
    # Include analysis context if requested
    if request.include_analysis_context and request.analysis_id:
        results = get_analysis_results(request.analysis_id)
        if results:
            context = f"Analysis {request.analysis_id}: {len(results)} detections"
    
    response = chatbot.chat(request.message, include_context=context)
    
    return ChatResponse(
        response=response,
        conversation_length=len(chatbot.conversation_history)
    )


@router.post("/chat/clear")
async def clear_chat_history(current_user: dict = Depends(get_current_user)):
    """Clear chatbot conversation history."""
    chatbot.clear_history()
    return {"status": "cleared", "message": "Conversation history cleared"}


@router.post("/chat/summarize/{analysis_id}")
async def summarize_analysis(analysis_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get AI-generated summary of analysis results.
    """
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    results = get_analysis_results(analysis_id)
    if not results:
        raise HTTPException(status_code=404, detail="No analysis results")
    
    summary = chatbot.get_analysis_summary({
        "analysis_id": analysis_id,
        "total_detections": len(results),
        "clusters": results[:5]  # First 5 for context
    })
    
    return {
        "analysis_id": analysis_id,
        "summary": summary,
        "total_detections": len(results)
    }
