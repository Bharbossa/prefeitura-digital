import os
import requests
from dotenv import load_dotenv

# Load local .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

print("--- Testando Z-API ---")
ZAPI_INSTANCE_ID = os.environ.get("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.environ.get("ZAPI_TOKEN")

if not ZAPI_INSTANCE_ID or not ZAPI_TOKEN:
    print("ERRO: Credenciais do Z-API ausentes.")
else:
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/status"
    try:
        # Check instance status
        headers = {}
        ZAPI_CLIENT_TOKEN = os.environ.get("ZAPI_CLIENT_TOKEN")
        if ZAPI_CLIENT_TOKEN:
            headers["Client-Token"] = ZAPI_CLIENT_TOKEN
        res = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            print("Z-API Resposta:", res.json())
        else:
            print("Z-API Erro:", res.text)
    except Exception as e:
        print("Erro de conexao Z-API:", e)

print("\n--- Testando Twilio ---")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
    print("ERRO: Credenciais do Twilio ausentes.")
else:
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        # Enviar SMS de teste para o proprio numero Twilio ou um numero verificado
        # OBS: Contas trial só enviam para numeros verificados. Vamos tentar enviar para o numero do usuário (que deve ser o dele)
        # Since we don't have the user's personal phone in env, we will just fetch the account to verify it's working fully.
        account = client.api.v2010.accounts(TWILIO_ACCOUNT_SID).fetch()
        print(f"Twilio Status: Conta '{account.friendly_name}' conectada. (Status: {account.status})")
        print("Para enviar um SMS real, adicione `client.messages.create(body='Teste', from_=TWILIO_PHONE_NUMBER, to='SEU_NUMERO')`")
    except Exception as e:
        print("Erro de conexao Twilio:", e)
