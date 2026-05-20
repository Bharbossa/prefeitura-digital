# backend/app/utils/notification_helper.py
import logging
from sqlalchemy.orm import Session
from ..models.schema import AdminSecretaria, Usuario, TipoUsuario
from .sms_service import send_status_sms

logger = logging.getLogger("NOTIFICATION_HELPER")

def notify_admins_of_new_record(db: Session, secretaria_id: int, message: str):
    """
    Notifies all sub-administrators of a specific department and also the general administrator.
    """
    try:
        # 1. Notify Sub-Administrators of the department
        subadmins = db.query(AdminSecretaria).filter(AdminSecretaria.secretaria_id == secretaria_id).all()
        for sa in subadmins:
            if sa.telefone:
                send_status_sms(sa.telefone, message)
        
        # 2. Notify General Administrator(s)
        # Global admins are in the 'usuarios' table with tipo_usuario='admin'
        global_admins = db.query(Usuario).filter(Usuario.tipo_usuario == TipoUsuario.admin).all()
        for ga in global_admins:
            if ga.telefone:
                send_status_sms(ga.telefone, f"[GLOBAL] {message}")
                
    except Exception as e:
        logger.error(f"Erro ao disparar notificações para administradores: {str(e)}")
