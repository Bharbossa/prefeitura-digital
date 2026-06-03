# sms_service.py
import logging
import os

# Configure logging to see SMS simulation in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SMS_SERVICE")

# Z-API Configuration Variables are retrieved dynamically in the function

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
    
    ZAPI_INSTANCE_ID = os.environ.get("ZAPI_INSTANCE_ID", "")
    ZAPI_TOKEN = os.environ.get("ZAPI_TOKEN", "")
    ZAPI_CLIENT_TOKEN = os.environ.get("ZAPI_CLIENT_TOKEN", "")

    if ZAPI_INSTANCE_ID and ZAPI_TOKEN:
        import requests
        try:
            # Endpoint padrão do Z-API para envio de texto
            url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
            
            payload = {
                "phone": clean_phone, # Z-API aceita o formato 5511999999999 sem o +
                "message": message
            }
            
            headers = {}
            if ZAPI_CLIENT_TOKEN:
                headers["Client-Token"] = ZAPI_CLIENT_TOKEN
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                logger.info(f"WhatsApp enviado para {clean_phone} via Z-API.")
                return True
            else:
                logger.error(f"Erro no Z-API ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"Exceção ao enviar via Z-API para {clean_phone}: {str(e)}")
            # Fallback para simulação em caso de erro
            pass

    logger.info(f"--- SMS SIMULADO ---")
    logger.info(f"PARA: {formatted_phone}")
    logger.info(f"MENSAGEM: {message}")
    logger.info(f"--------------------")
    
    return True

def get_resolved_message(titulo: str):
    return "OBRIGADO POR USAR O COLÔNIA DIGITAL. SUA SOLICITAÇÃO JÁ FOI RESOLVIDA!"

def get_progress_message(titulo: str):
    return f"COLÔNIA DIGITAL: Sua solicitação ({titulo}) está EM ANDAMENTO e sendo analisada pela nossa equipe."

def get_cancelled_message(titulo: str):
    return f"COLÔNIA DIGITAL: Sua solicitação ({titulo}) foi CANCELADA."

def get_confirmed_message(assunto: str, data_hora: str):
    return f"COLÔNIA DIGITAL: Seu agendamento ({assunto}) para {data_hora} foi CONFIRMADO."

def send_password_sms(phone: str, password: str):
    message = f"COLÔNIA DIGITAL: Sua nova senha e: {password}. Recomendamos altera-la apos o login."
    return send_status_sms(phone, message)
