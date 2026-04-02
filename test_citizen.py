import requests
import json

base_url = "https://prefeitura-digital.onrender.com/api"
# 1. create citizen
register_data = {
    "nome": "Test Citizen",
    "cpf": "12345678901",
    "email": "citizen_test500@teste.com",
    "senha": "123",
    "telefone": "1199999999"
}

r1 = requests.post(f"{base_url}/auth/register", json=register_data)
print("Register:", r1.status_code, r1.text)

# 2. Login
login_data = {
    "username": "citizen_test500@teste.com",
    "password": "123"
}
r2 = requests.post(f"{base_url}/auth/login", data=login_data)
print("Login:", r2.status_code)
if r2.status_code != 200:
    exit(1)
token = r2.json()["access_token"]

# 3. Create agendamento
payload = {
    "secretaria_id": 15,
    "tipo": "Consulta Presencial",
    "assunto": "[POSTO CENTRO (PSF 02)] queda de moto",
    "motivo": None,
    "acompanhante": None,
    "data_hora": "2026-03-31T12:40:00.000Z",
    "cartao_sus": "54846174561248941564"
}
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

r3 = requests.post(f"{base_url}/agendamentos", json=payload, headers=headers)
print("Agendamento:", r3.status_code)
print("Response:", r3.text)
