import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

# Load env vars from backend/.env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

from app.utils.sms_service import send_status_sms

# Get phone number from arguments or prompt
if len(sys.argv) > 1:
    phone = sys.argv[1]
else:
    phone = input("Digite o numero de telefone com DDD (ex: 81999999999): ")

print(f"Enviando mensagem de teste para {phone}...")
success = send_status_sms(phone, "🚀 *Colônia Digital*\n\nEste é um teste oficial de notificação do sistema via Z-API. A configuração foi um sucesso!")

if success:
    print("Comando executado. Verifique os logs e o WhatsApp de destino.")
else:
    print("Falha ao enviar.")
