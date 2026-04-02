import requests
import json

URL = "https://prefeitura-digital.onrender.com/api"
email = "allyson@leopoldina.gov.br"
password = "123456"

print("1. Login...")
res = requests.post(f"{URL}/auth/login", data={"username": email, "password": password})
if res.status_code != 200:
    print(f"Login failed: {res.status_code} {res.text}")
    exit(1)

token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("Token acquired.")

print("\n2. /auth/me")
me_res = requests.get(f"{URL}/auth/me", headers=headers)
print(me_res.status_code, me_res.text[:100])

print("\n3. /admin/metrics/summary")
sum_res = requests.get(f"{URL}/admin/metrics/summary", headers=headers)
print(sum_res.status_code, sum_res.text[:100])

print("\n4. /ocorrencias")
oc_res = requests.get(f"{URL}/ocorrencias", headers=headers)
print(oc_res.status_code, oc_res.text[:100])

print("\nDONE!")
