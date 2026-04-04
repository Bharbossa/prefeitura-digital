
import requests

def test_system_admin():
    base_url = "https://prefeitura-digital.onrender.com/api"
    login_payload = {"username": "admin@leopoldina.gov.br", "password": "123"}
    
    print("Logando como System Admin...")
    res = requests.post(f"{base_url}/auth/login", data=login_payload)
    if res.status_code != 200:
        print(f"Erro no login: {res.text}")
        return
    
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Buscando /ocorrencias...")
    res_oc = requests.get(f"{base_url}/ocorrencias", headers=headers)
    print(f"Status /ocorrencias: {res_oc.status_code}")
    print(f"Response: {res_oc.text}")

if __name__ == "__main__":
    test_system_admin()
