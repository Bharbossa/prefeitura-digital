import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EMAIL_SERVICE")

# Configurações de SMTP a partir de variáveis de ambiente
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
port_env = os.environ.get("SMTP_PORT", "587")
try:
    SMTP_PORT = int(port_env) if port_env else 587
except ValueError:
    SMTP_PORT = 587
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

def send_password_email(to_email: str, new_password: str) -> bool:
    """Envia a nova senha por e-mail para o usuário."""
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("Credenciais SMTP não configuradas. Simulando envio de e-mail.")
        logger.info(f"--- EMAIL SIMULADO PARA {to_email} ---")
        logger.info(f"Sua nova senha é: {new_password}")
        logger.info(f"----------------------------------------")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = "Colônia Digital - Recuperação de Senha"

        body = f"""Olá,

Você solicitou a recuperação de sua senha no sistema Colônia Digital.
Sua nova senha temporária é: {new_password}

Recomendamos que você acesse o sistema e altere esta senha o mais rápido possível na página do seu perfil.

Atenciosamente,
Equipe Colônia Digital
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USER, to_email, text)
        server.quit()
        logger.info(f"E-mail enviado com sucesso para {to_email}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail para {to_email}: {str(e)}")
        return False
