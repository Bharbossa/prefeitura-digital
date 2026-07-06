from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.schema import Usuario, LogAuditoria
from ..core.auth_deps import get_current_user
from ..utils.sms_service import notify_subadmins_background

router = APIRouter()

@router.post("")
def trigger_panic_button(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    # Ensure current user is an actual Usuario
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")
        
    user = db_sql.query(Usuario).filter(Usuario.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    if getattr(user, 'botao_panico_autorizado', 0) != 1:
        raise HTTPException(status_code=403, detail="Você não tem autorização para utilizar o Botão do Pânico.")

    # Mount the message
    msg = f"🚨 ALERTA DE PÂNICO 🚨\nA usuária {user.nome} acionou o Botão do Pânico!\nTel: {user.telefone}\nEndereço: {user.endereco}"
    
    # 17 is the GUARDA MUNICIPAL
    background_tasks.add_task(notify_subadmins_background, 17, msg)
    
    # Audit log
    log = LogAuditoria(
        usuario_id=user.id,
        usuario_tipo="cidadao",
        acao="botao_panico",
        detalhes=f"Acionou o Botão do Pânico"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Alerta enviado com sucesso para a Guarda Municipal."}
