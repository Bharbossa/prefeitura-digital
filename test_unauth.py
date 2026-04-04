
import requests

def test_unauthenticated():
    url = "https://prefeitura-digital.onrender.com/api/ocorrencias"
    print(f"Testando {url} SEM TOKEN...")
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text}")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    test_unauthenticated()
