
import requests

def test_subadmin():
    base_url = "https://prefeitura-digital.onrender.com/api"
    login_payload = {"username": "infra@teste.com", "password": "123"}
    
    print("Logando como Sub-Admin...")
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
    test_subadmin()
