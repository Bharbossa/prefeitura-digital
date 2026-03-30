from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from ..database import get_db
from ..models.schema import Secretaria
from ..core.firebase_config import db, DB_MODE

router = APIRouter()

class SecretariaResponse(BaseModel):
    id: str
    nome: str

@router.get("", response_model=List[SecretariaResponse])
def get_secretarias(db_sql: Session = Depends(get_db)):
    try:
        if DB_MODE == "firestore":
            docs = db.collection("secretarias").get()
            return [{"id": d.id, "nome": d.to_dict().get("nome")} for d in docs]
        else:
            # SQL Fallback
            secs = db_sql.query(Secretaria).all()
            return [{"id": str(s.id), "nome": s.nome} for s in secs]
    except Exception as e:
        with open("debug_error.txt", "a") as f:
            f.write(f"Error in get_secretarias: {str(e)}\n")
        raise e
