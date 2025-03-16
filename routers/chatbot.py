from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from collections import deque
from typing import List

from models.schema import ChatbotRequest, ChatbotResponse
from config.database import get_session
from models.models import ChatbotInteraction, User
from rag.query_engine import get_query_engine
from routers.auth import get_current_user

router = APIRouter()

MAX_HISTORY = 5  # Maximum conversation history

# POST endpoint: expects a JSON body conforming to ChatbotRequest
@router.post("/chatbot/")
async def chatbot_post(
    query: ChatbotRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    query_engine=Depends(get_query_engine)
):
    """
    API endpoint for the chatbot via POST.

    Request (JSON body):
    {
        "user_input": "What CreditChek?"
    }

    Response:
    {
        "user_input": "What CreditChek?",
        "response": "CreditChek is a ...",
        "timestamp": "2024-01-29T12:34:56Z"
    }
    """
    user_input = query.user_input.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="User input cannot be empty")

    # Retrieve user's past conversation history
    past_messages = db.query(ChatbotInteraction).filter(
        ChatbotInteraction.user_id == current_user.id
    ).order_by(ChatbotInteraction.timestamp.desc()).limit(MAX_HISTORY).all()

    history = deque(maxlen=MAX_HISTORY)
    for msg in reversed(past_messages):
        history.append(msg.user_input)
        history.append(msg.response)

    # Generate chatbot response using the query engine
    bot_response = query_engine.query(user_input)
    response : str = bot_response.response

    # Save interaction to the database
    chat_record = ChatbotInteraction(
        user_id=current_user.id,
        user_input=user_input,
        response=bot_response.response,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(chat_record)
    db.commit()

    return {
        "user_input": user_input,
        "response": response,
        "timestamp": chat_record.timestamp
    }


@router.get("/chatbot/history/")
async def get_chat_history(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    chat_history = db.query(ChatbotInteraction).filter(
        ChatbotInteraction.user_id == current_user.id
    ).order_by(ChatbotInteraction.timestamp.asc()).all()

    return chat_history

