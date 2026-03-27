# sms_service.py
import logging

# Configure logging to see SMS simulation in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SMS_SERVICE")

def send_status_sms(phone: str, message: str):
    """
    Simulates sending an SMS. 
    In a real production environment, this would integrate with a provider like Twilio, Sinch, etc.
    """
    if not phone:
        logger.warning("Tentativa de envio de SMS sem número de telefone.")
        return False
    
    # Clean phone number (simulated)
    clean_phone = "".join(filter(str.isdigit, phone))
    
    logger.info(f"--- SMS SIMULADO ---")
    logger.info(f"PARA: {clean_phone}")
    logger.info(f"MENSAGEM: {message}")
    logger.info(f"--------------------")
    
    return True

def get_resolved_message(titulo: str):
    return f"AGRADECEMOS POR USAR NOSSO SISTEMA E INFORMAMOS QUE SEU PROBLEMA ({titulo}) FOI RESOLVIDO"

def get_confirmed_message(assunto: str, data_hora: str):
    return f"COLÔNIA DIGITAL: Seu agendamento ({assunto}) para {data_hora} foi CONFIRMADO."

def send_password_sms(phone: str, password: str):
    message = f"COLÔNIA DIGITAL: Sua nova senha e: {password}. Recomendamos altera-la apos o login."
    return send_status_sms(phone, message)
