from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.schema import ChatIA, Usuario
from ..models.pydantic_schemas import ChatIARequest, ChatIAResponse
from ..core.security import SECRET_KEY, ALGORITHM
from jose import jwt
from sqlalchemy import func
import google.generativeai as genai
import os

router = APIRouter()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

security = HTTPBearer(auto_error=False)

def get_optional_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)):
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email:
            user = db.query(Usuario).filter(func.lower(Usuario.email) == func.lower(email)).first()
            if user: return user.id
    except:
        pass
    return None


@router.post("/", response_model=ChatIAResponse)
async def chat_with_ia(request: ChatIARequest, user_id: Optional[int] = Depends(get_optional_user_id), db: Session = Depends(get_db)):
    mensagem_usuario = request.mensagem
    resposta_ia = ""
    
    if not GOOGLE_API_KEY:
        # Modo simulação se a chave não estiver configurada
        resposta_ia = f"Olá, cidadão! Você disse: '{mensagem_usuario}'. Sou o assistente virtual da Colônia Digital. No momento estou em modo de simulação (Chave API não configurada)."
    else:
        try:
            # Inicializa o modelo Gemini com instruções de sistema
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction="Você é um assistente virtual da Colônia Digital. Sua função é responder de forma curta e objetiva apenas a perguntas simples e diretas sobre a prefeitura e suas secretarias. Se o usuário fizer uma pergunta complexa, técnica, política ou fora do escopo municipal, informe educadamente que ele deve procurar a secretaria responsável ou o atendimento presencial para orientações detalhadas."
            )
            
            # Gera a resposta
            response = model.generate_content(mensagem_usuario)
            resposta_ia = response.text
            
        except Exception as e:
            print(f"Erro no Gemini: {str(e)}")
            raise HTTPException(status_code=500, detail="Ocorreu um erro ao processar sua solicitação com a IA.")
            
    # Salva a interação no banco de dados para auditoria
    chat_entry = ChatIA(
        mensagem_usuario=mensagem_usuario,
        resposta_ia=resposta_ia,
        usuario_id=user_id
    )
    db.add(chat_entry)
    db.commit()
    db.refresh(chat_entry)
    
    return ChatIAResponse(resposta=resposta_ia)
