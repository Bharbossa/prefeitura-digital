
import requests

def verify_me():
    base_url = "https://prefeitura-digital.onrender.com/api"
    login_payload = {"username": "super@teste.com", "password": "123"}
    
    print("Logando como Super Admin...")
    res = requests.post(f"{base_url}/auth/login", data=login_payload)
    if res.status_code != 200:
        print(f"Erro no login: {res.text}")
        return
    
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Buscando /auth/me...")
    res_me = requests.get(f"{base_url}/auth/me", headers=headers)
    print(f"Status /auth/me: {res_me.status_code}")
    print(f"Response: {res_me.text}")

if __name__ == "__main__":
    verify_me()
