
import requests

def test_debug_raw():
    url = "https://prefeitura-digital.onrender.com/api/ocorrencias/debug-raw"
    print(f"Testando {url}...")
    try:
        res = requests.get(url)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"Total: {len(data)}")
            if len(data) > 0:
                print(f"Exemplo: {data[0]}")
        else:
            print(f"Erro: {res.text}")
    except Exception as e:
        print(f"Falha: {e}")

if __name__ == "__main__":
    test_debug_raw()
