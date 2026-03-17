from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.schema import ChatIA
from ..models.pydantic_schemas import ChatIARequest, ChatIAResponse
from ..core.auth_deps import get_current_user
import httpx
import os

router = APIRouter()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

@router.post("/", response_model=ChatIAResponse)
async def chat_with_ia(request: ChatIARequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    # Simple Mock if no API key is set
    mensagem_usuario = request.mensagem
    resposta_ia = ""
    
    if not OPENAI_API_KEY:
        resposta_ia = f"Olá, cidadão! Você disse: '{mensagem_usuario}'. Sou o assistente virtual da prefeitura. Em que posso ajudar? (Modo Simulação)"
    else:
        # Send request to OpenAI API (example integration)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": "Você é um assistente virtual da prefeitura de Leopoldina voltado a ajudar os cidadãos a escolherem a secretaria certa para os problemas e a tirarem dúvidas sobre a plataforma digital de ocorrências urbanas."},
                            {"role": "user", "content": mensagem_usuario}
                        ]
                    },
                    timeout=10.0
                )
                data = response.json()
                resposta_ia = data['choices'][0]['message']['content']
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    # Save the interaction to the DB
    chat_entry = ChatIA(
        mensagem_usuario=mensagem_usuario,
        resposta_ia=resposta_ia,
        usuario_id=current_user.id
    )
    db.add(chat_entry)
    db.commit()
    db.refresh(chat_entry)
    
    return ChatIAResponse(resposta=resposta_ia)
