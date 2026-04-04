
import requests

def test_login():
    url = "https://prefeitura-digital.onrender.com/api/auth/login"
    payload = {
        "username": "infra@teste.com",
        "password": "123"
    }
    
    print(f"Testando login para {payload['username']}...")
    try:
        response = requests.post(url, data=payload)
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text}")
    except Exception as e:
        print(f"Erro na requisição: {e}")

if __name__ == "__main__":
    test_login()
