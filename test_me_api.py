
import requests

def test_me():
    login_url = "https://prefeitura-digital.onrender.com/api/auth/login"
    login_payload = {
        "username": "infra@teste.com",
        "password": "123"
    }
    
    print(f"Logando...")
    res = requests.post(login_url, data=login_payload)
    if res.status_code == 200:
        token = res.json()["access_token"]
        me_url = "https://prefeitura-digital.onrender.com/api/auth/me"
        print(f"Buscando /me...")
        headers = {"Authorization": f"Bearer {token}"}
        res_me = requests.get(me_url, headers=headers)
        print(f"Status /me: {res_me.status_code}")
        print(f"Resposta /me: {res_me.text}")
    else:
        print(f"Falha no login: {res.text}")

if __name__ == "__main__":
    test_me()
