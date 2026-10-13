# backend/app/utils/notification_helper.py
import logging
import threading
from sqlalchemy.orm import Session
from ..models.schema import AdminSecretaria, Usuario, TipoUsuario
from .sms_service import send_status_sms

logger = logging.getLogger("NOTIFICATION_HELPER")

def _notify_admins_thread(secretaria_id: int, custom_msg: str = None):
    from ..database import SessionLocal
    from .sms_service import send_status_sms, get_gcm_subadmins_and_admins
    db = SessionLocal()
    try:
        message = custom_msg or "NOVA SOLICITAÇÃO DE SERVIÇO. Entre no Sistema e veja a solicitação do cidadão!"
        
        dest_phones = get_gcm_subadmins_and_admins(db, secretaria_id)
        
        for phone in dest_phones:
            msg_to_send = "COLÔNIA DIGITAL: Cadastro unico! Existe uma nova solicitação de serviço!" if secretaria_id == 22 else message
            send_status_sms(phone, msg_to_send)
    except Exception as e:
        logger.error(f"Erro ao disparar notificações para administradores: {str(e)}")
    finally:
        db.close()

def notify_admins_of_new_record(db: Session, secretaria_id: int, message: str = None):
    """
    Notifies all sub-administrators of a specific department and also the general administrator in background.
    """
    t = threading.Thread(target=_notify_admins_thread, args=(secretaria_id, message))
    t.start()
