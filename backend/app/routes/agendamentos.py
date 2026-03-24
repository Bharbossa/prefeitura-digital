from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.schema import Usuario, AdminSecretaria, Agendamento
from ..models.pydantic_schemas import AgendamentoCreate, AgendamentoResponse
from ..core.auth_deps import get_current_user

router = APIRouter()

@router.post("/", response_model=AgendamentoResponse)
def criar_agendamento(agend: AgendamentoCreate, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if not isinstance(current_user, Usuario):
        raise HTTPException(status_code=403, detail="Apenas cidadãos podem criar agendamentos pelo perfil.")
    
    novo_agendamento = Agendamento(
        usuario_id=current_user.id,
        secretaria_id=agend.secretaria_id,
        tipo=agend.tipo,
        assunto=agend.assunto,
        data_hora=agend.data_hora
    )
    db_sql.add(novo_agendamento)
    db_sql.commit()
    db_sql.refresh(novo_agendamento)
    return novo_agendamento

@router.get("/", response_model=List[AgendamentoResponse])
def listar_meus_agendamentos(current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if isinstance(current_user, Usuario) and current_user.tipo_usuario_verificado != "admin":
        # Cidadão lista apenas os seus próprios agendamentos
        return db_sql.query(Agendamento).filter(Agendamento.usuario_id == current_user.id).order_by(Agendamento.data_hora.desc()).all()
    
    # Se for admin geral
    if isinstance(current_user, Usuario) and current_user.tipo_usuario_verificado == "admin":
        return db_sql.query(Agendamento).order_by(Agendamento.data_hora.desc()).all()
    
    # Se for sub-admin de secretaria
    if isinstance(current_user, AdminSecretaria):
        return db_sql.query(Agendamento).filter(Agendamento.secretaria_id == current_user.secretaria_id).order_by(Agendamento.data_hora.desc()).all()
    
    raise HTTPException(status_code=403, detail="Não autorizado.")

@router.patch("/{agend_id}/status")
def atualizar_status(agend_id: int, status: str, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if status not in ["Confirmado", "Cancelado", "Pendente"]:
        raise HTTPException(status_code=400, detail="Status inválido.")
        
    agendamento = db_sql.query(Agendamento).filter(Agendamento.id == agend_id).first()
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    
    if isinstance(current_user, AdminSecretaria):
        if agendamento.secretaria_id != current_user.secretaria_id:
            raise HTTPException(status_code=403, detail="Agendamento pertence a outra secretaria.")
            
    agendamento.status = status
    db_sql.commit()
    return {"message": "Status atualizado com sucesso"}
