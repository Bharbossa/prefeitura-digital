import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from app.utils.sms_service import notify_custom_message_background

print("Iniciando envio de teste 'Bom dia' para todos os numeros cadastrados...")
notify_custom_message_background("Bom dia!")
print("Envio finalizado.")
