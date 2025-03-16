from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from collections import deque
from typing import Any, List

from models.schema import ChatbotRequest, ChatbotResponse
from config.database import get_session
from models.models import ChatbotInteraction, User
from rag.query_engine import get_query_engine
from routers.auth import get_current_user

router = APIRouter()

MAX_HISTORY = 5  # Maximum conversation history

prompt = """
You are Mark Musk, a GenAI developer assistant bot designed to assist software engineers in integrating REST API products efficiently. You provide guidance and generate sample code in various programming languages, including Python, Node.js (or NestJS), PHP Laravel, and GoLang, among others. Your goal is to help developers integrate APIs 10 times faster.

When a developer asks about integrating a specific REST API, follow these steps:

1. **Understand the API**: Analyze the API's functionality and its endpoints.

2. **Identify the Programming Language**: Determine the developer's preferred programming language. If not specified, ask for it.

3. **Provide Integration Steps**: Outline the necessary steps to integrate the API in the chosen language.

4. **Generate Sample Code**: Provide a complete, functional code snippet demonstrating the integration.

5. **Offer Additional Assistance**: Ask if the developer needs further help or clarification.

Ensure that your responses are clear, concise, and tailored to the developer's needs.
"""

# POST endpoint: expects a JSON body conforming to ChatbotRequest
@router.post("/chatbot/", response_model=None)
async def chatbot_post(
    query: ChatbotRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    query_engine=Depends(get_query_engine)
)-> Any:
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
    bot_response = query_engine.query(prompt + user_input)
    response: str = bot_response.response

    # Save interaction to the database
    chat_record = ChatbotInteraction(
        user_id=current_user.id,
        user_input=user_input,
        response=bot_response.response,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(chat_record)
    db.commit()

    return ChatbotResponse(
        user_input=user_input,
        response=response,
        timestamp=chat_record.timestamp
    )


@router.get("/chatbot/history/", response_model=None)
async def get_chat_history(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
)-> Any:
    chat_history = db.query(ChatbotInteraction).filter(
        ChatbotInteraction.user_id == current_user.id
    ).order_by(ChatbotInteraction.timestamp.asc()).all()

    return chat_history

