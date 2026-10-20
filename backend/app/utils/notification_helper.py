# backend/app/utils/notification_helper.py
import logging
import threading
from sqlalchemy.orm import Session
from ..models.schema import AdminSecretaria, Usuario, TipoUsuario
from .sms_service import send_status_sms

logger = logging.getLogger("NOTIFICATION_HELPER")

def _notify_admins_thread(secretaria_id: int, custom_msg: str = None, extra_context: str = None):
    import time
    from ..database import SessionLocal
    from .sms_service import send_status_sms, get_subadmins_and_admins
    db = SessionLocal()
    try:
        if custom_msg:
            msg_to_send = custom_msg
        elif secretaria_id == 22:
            msg_to_send = "COLÔNIA DIGITAL: Assistência Social / Cadastro Único! Existe uma nova solicitação de serviço."
        else:
            msg_to_send = "COLÔNIA DIGITAL: NOVA SOLICITAÇÃO DE SERVIÇO. Entre no Sistema e veja a solicitação do cidadão!"
        
        dest_phones = get_subadmins_and_admins(db, secretaria_id, extra_context=extra_context or custom_msg)
        logger.info(f"Disparando SMS para {len(dest_phones)} destinatários (sec_id: {secretaria_id}): {dest_phones}")
        
        for phone in dest_phones:
            send_status_sms(phone, msg_to_send)
            time.sleep(0.3)
    except Exception as e:
        logger.error(f"Erro ao disparar notificações para administradores: {str(e)}")
    finally:
        db.close()

def notify_admins_of_new_record(db: Session, secretaria_id: int, message: str = None, extra_context: str = None):
    """
    Notifies all sub-administrators of a specific department and also the general administrator in background.
    """
    t = threading.Thread(target=_notify_admins_thread, args=(secretaria_id, message, extra_context))
    t.start()
