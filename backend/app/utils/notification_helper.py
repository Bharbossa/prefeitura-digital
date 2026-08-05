# backend/app/utils/notification_helper.py
import logging
import threading
from sqlalchemy.orm import Session
from ..models.schema import AdminSecretaria, Usuario, TipoUsuario
from .sms_service import send_status_sms

logger = logging.getLogger("NOTIFICATION_HELPER")

def _notify_admins_thread(secretaria_id: int):
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        message = "NOVA SOLICITAÇÃO DE SERVIÇO. Entre no Sistema e veja a solicitação do cidadão!"
        
        # 1. Notify Sub-Administrators of the department
        subadmins = db.query(AdminSecretaria).filter(AdminSecretaria.secretaria_id == secretaria_id).all()
        for sa in subadmins:
            if sa.telefone:
                # Custom message for Assistencia Social (ID 22) sub-admins
                custom_msg = "COLÔNIA DIGITAL: Cadastro unico! Existe uma nova solicitação de serviço!" if secretaria_id == 22 else message
                send_status_sms(sa.telefone, custom_msg)
        
        # 2. Notify General Administrator(s)
        global_admins = db.query(Usuario).filter(Usuario.tipo_usuario == TipoUsuario.admin).all()
        for ga in global_admins:
            if ga.telefone:
                send_status_sms(ga.telefone, message)
    except Exception as e:
        logger.error(f"Erro ao disparar notificações para administradores: {str(e)}")
    finally:
        db.close()

def notify_admins_of_new_record(db: Session, secretaria_id: int, message: str):
    """
    Notifies all sub-administrators of a specific department and also the general administrator in background.
    """
    t = threading.Thread(target=_notify_admins_thread, args=(secretaria_id,))
    t.start()
