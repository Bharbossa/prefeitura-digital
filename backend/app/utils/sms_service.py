# sms_service.py
import logging
import os

# Configure logging to see SMS simulation in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SMS_SERVICE")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")

def send_status_sms(phone: str, message: str):
    """
    Sends an SMS using Twilio if configured, else simulates sending. 
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
    
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            client_msg = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=formatted_phone
            )
            logger.info(f"SMS enviado para {formatted_phone}: SID {client_msg.sid}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar SMS via Twilio para {formatted_phone}: {str(e)}")
            # Fallback to simulation if there's an error
            pass

    logger.info(f"--- SMS SIMULADO ---")
    logger.info(f"PARA: {formatted_phone}")
    logger.info(f"MENSAGEM: {message}")
    logger.info(f"--------------------")
    
    return True

def get_resolved_message(titulo: str):
    return "OBRIGADO POR USAR O COLÔNIADIGITAL! seu problema foi resolvido com sucesso."

def get_confirmed_message(assunto: str, data_hora: str):
    return f"COLÔNIA DIGITAL: Seu agendamento ({assunto}) para {data_hora} foi CONFIRMADO."

def send_password_sms(phone: str, password: str):
    message = f"COLÔNIA DIGITAL: Sua nova senha e: {password}. Recomendamos altera-la apos o login."
    return send_status_sms(phone, message)
