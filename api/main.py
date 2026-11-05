from fastapi import FastAPI, Depends
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.orm import Session
from database.models import get_db, Message, init_db
from brain.llm_client import LLMClient
from core.logger import get_logger

log = get_logger(__name__)
app = FastAPI(title="JARVIS AI Backend", version="1.0.0")
llm = LLMClient()

class ChatRequest(BaseModel):
    prompt: str
    language: Literal["en", "ur"] = "en"
    conversation_id: int | None = None

@app.on_event("startup")
def startup_event():
    # Make sure DB tables exist when the server starts
    init_db()

@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    log.info(f"Received prompt: {request.prompt}")
    
    # 1. Get response from Ollama
    response_text = await llm.generate_response(
        request.prompt,
        language=request.language,
    )
    
    # 2. Save to PostgreSQL
    db_message = Message(
        conversation_id=request.conversation_id or 1, 
        role="user", 
        content=request.prompt
    )
    db.add(db_message)
    db.commit()
    
    return {
        "status": "success",
        "response": response_text,
        "conversation_id": request.conversation_id or 1
    }