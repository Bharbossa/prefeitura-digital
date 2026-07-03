# sms_service.py
import logging
import os
import time
# Configure logging to see SMS simulation in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SMS_SERVICE")

# Z-API Configuration Variables are retrieved dynamically in the function

def send_status_sms(phone: str, message: str):
    """
    Sends an SMS using Twilio.
    """
    if not phone:
        logger.warning("Tentativa de envio de SMS sem número de telefone.")
        return False
    
    # Clean phone number
    clean_phone = "".join(filter(str.isdigit, phone))
    # Usually Brazil uses +55
    if not clean_phone.startswith("55"):
        clean_phone = "55" + clean_phone
    formatted_phone = "+" + clean_phone
    
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message_twilio = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=formatted_phone
            )
            logger.info(f"SMS enviado para {formatted_phone} via Twilio (SID: {message_twilio.sid})")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar via Twilio para {formatted_phone}: {str(e)}")
            return False
            
    logger.info(f"--- SMS SIMULADO (TWILIO NÃO CONFIGURADO) ---")
    logger.info(f"PARA: {formatted_phone}")
    logger.info(f"MENSAGEM: {message}")
    logger.info(f"--------------------")
    
    return True

def get_resolved_message(titulo: str):
    return "OBRIGADO POR USAR O COLÔNIA DIGITAL. SUA SOLICITAÇÃO FOI FINALIZADA!"

def get_progress_message(titulo: str):
    return f"COLÔNIA DIGITAL: Sua solicitação ({titulo}) está EM ANDAMENTO e sendo analisada pela nossa equipe."

def get_cancelled_message(titulo: str):
    return f"COLÔNIA DIGITAL: Sua solicitação ({titulo}) foi CANCELADA."

def get_confirmed_message(assunto: str, data_hora: str):
    return f"COLÔNIA DIGITAL: Seu agendamento ({assunto}) para {data_hora} foi CONFIRMADO."

def send_password_sms(phone: str, password: str):
    """
    Sends an SMS using Twilio for new password requests.
    """
    message = f"COLÔNIA DIGITAL: Sua nova senha e: {password}. Recomendamos altera-la apos o login."
    
    if not phone:
        logger.warning("Tentativa de envio de senha sem número de telefone.")
        return False
        
    clean_phone = "".join(filter(str.isdigit, phone))
    
    if not clean_phone.startswith("55"):
        clean_phone = "55" + clean_phone
    formatted_phone = "+" + clean_phone
    
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message_twilio = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=formatted_phone
            )
            logger.info(f"Senha enviada para {formatted_phone} via Twilio (SID: {message_twilio.sid})")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar senha via Twilio para {formatted_phone}: {str(e)}")
            return False
            
    logger.info(f"--- SMS SIMULADO (TWILIO NÃO CONFIGURADO) ---")
    logger.info(f"PARA: {formatted_phone}")
    logger.info(f"MENSAGEM: {message}")
    logger.info(f"--------------------")
    
    return True

def notify_subadmins_background(secretaria_id: int, message: str):
    from app.database import SessionLocal
    from app.models.schema import AdminSecretaria
    db = SessionLocal()
    try:
        subadmins = db.query(AdminSecretaria).filter(AdminSecretaria.secretaria_id == secretaria_id).all()
        for sub in subadmins:
            phone = getattr(sub, 'telefone', None)
            if phone:
                send_status_sms(phone, message)
    except Exception as e:
        logger.error(f"Erro em notify_subadmins_background: {e}")
    finally:
        db.close()

def notify_all_users_background(alert_message: str, aviso_id: int = None):
    from app.database import SessionLocal
    from app.models.schema import Usuario, Aviso, AdminSecretaria
    db = SessionLocal()
    try:
        users = db.query(Usuario).all()
        subadmins = db.query(AdminSecretaria).all()
        
        unique_phones = set()
        sucessos = 0
        
        # Helper to process a phone
        def process_phone(phone):
            nonlocal sucessos
            if phone and len(''.join(filter(str.isdigit, phone))) >= 10:
                clean_phone = "".join(filter(str.isdigit, phone))
                if clean_phone not in unique_phones:
                    unique_phones.add(clean_phone)
                    if send_status_sms(clean_phone, alert_message):
                        sucessos += 1
                    time.sleep(1) # Sleep to avoid rate limits

        for u in users:
            process_phone(getattr(u, 'telefone', None))
            
        for sa in subadmins:
            process_phone(getattr(sa, 'telefone', None))

        if aviso_id:
            aviso = db.query(Aviso).filter(Aviso.id == aviso_id).first()
            if aviso:
                aviso.destinatarios_alcancados = sucessos
                db.commit()
    except Exception as e:
        logger.error(f"Erro em notify_all_users_background: {e}")
    finally:
        db.close()

def notify_custom_message_background(message: str):
    from app.database import SessionLocal
    from app.models.schema import Usuario
    db = SessionLocal()
    try:
        users = db.query(Usuario).all()
        unique_phones = set()
        sucessos = 0
        for u in users:
            phone = getattr(u, 'telefone', None)
            if phone and len(''.join(filter(str.isdigit, phone))) >= 10:
                clean_phone = "".join(filter(str.isdigit, phone))
                if clean_phone not in unique_phones:
                    unique_phones.add(clean_phone)
                    if send_status_sms(clean_phone, message):
                        sucessos += 1
                    time.sleep(1) # Sleep to avoid rate limits
        logger.info(f"Mensagem customizada enviada com sucesso para {sucessos} destinatarios.")
    except Exception as e:
        logger.error(f"Erro em notify_custom_message_background: {e}")
    finally:
        db.close()
