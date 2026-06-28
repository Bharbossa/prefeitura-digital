from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.schema import Aviso
from ..models.pydantic_schemas import AvisoCreate, AvisoResponse
from ..core.auth_deps import get_current_user, get_current_admin

router = APIRouter()

@router.get("", response_model=List[AvisoResponse])
def get_avisos(db_sql: Session = Depends(get_db)):
    # Any user (or even public) can see active avisos
    avisos = db_sql.query(Aviso).filter(Aviso.ativo == 1).order_by(Aviso.data_criacao.desc()).all()
    return avisos

@router.post("", response_model=AvisoResponse)
def create_aviso(
    aviso_in: AvisoCreate, 
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_admin), 
    db_sql: Session = Depends(get_db)
):
    if current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores gerais podem criar avisos.")
    
    novo_aviso = Aviso(
        titulo=aviso_in.titulo,
        mensagem=aviso_in.mensagem,
        tipo=aviso_in.tipo,
        ativo=1,
        autor_id=current_user.id
    )
    db_sql.add(novo_aviso)
    db_sql.commit()
    db_sql.refresh(novo_aviso)
    
    # Audit log
    from ..models.schema import LogAuditoria
    log = LogAuditoria(
        usuario_id=current_user.id,
        usuario_tipo="admin",
        acao="Criou Aviso",
        detalhes=f"Aviso criado: {novo_aviso.titulo} ({novo_aviso.tipo})"
    )
    db_sql.add(log)
    db_sql.commit()
    
    from ..utils.sms_service import notify_all_users_background
    alerta_msg = f"ALERTA DA PREFEITURA: {novo_aviso.titulo} - {novo_aviso.mensagem}"
    background_tasks.add_task(notify_all_users_background, alerta_msg)
    
    return novo_aviso

@router.delete("/{aviso_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_aviso(
    aviso_id: int, 
    current_user = Depends(get_current_admin), 
    db_sql: Session = Depends(get_db)
):
    if current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas administradores gerais podem deletar avisos.")
    
    aviso = db_sql.query(Aviso).filter(Aviso.id == aviso_id).first()
    if not aviso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aviso não encontrado.")
    
    # Soft delete
    aviso.ativo = 0
    
    # Audit log
    from ..models.schema import LogAuditoria
    log = LogAuditoria(
        usuario_id=current_user.id,
        usuario_tipo="admin",
        acao="Deletou Aviso",
        detalhes=f"Aviso desativado: {aviso.titulo}"
    )
    db_sql.add(log)
    db_sql.commit()
    return
