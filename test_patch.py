import requests

URL = "https://prefeitura-digital.onrender.com/api"
email = "allyson@leopoldina.gov.br"
password = "123456"

print("1. Login...")
res = requests.post(f"{URL}/auth/login", data={"username": email, "password": password})
token = res.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

print("2. Get Agendamentos...")
ag = requests.get(f"{URL}/agendamentos", headers=headers).json()
if not ag:
    print("No agendamentos found.")
else:
    first_id = ag[0]['id']
    old_status = ag[0]['status']
    print(f"Agendamento to test: {first_id} (Status: {old_status})")
    
    # Try confirm
    patch_res = requests.patch(f"{URL}/agendamentos/{first_id}/status?status=Confirmado", headers=headers)
    print("PATCH Status:", patch_res.status_code)
    print("PATCH Response:", patch_res.text)
