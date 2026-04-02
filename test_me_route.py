import requests
import time

URL = "https://prefeitura-digital.onrender.com/api"

def test_login_and_me():
    print("Testing login for allyson@leopoldina.gov.br...")
    res = requests.post(f"{URL}/auth/login", data={'username':'allyson@leopoldina.gov.br', 'password':'123456'})
    if res.status_code != 200:
        print("Login falhou:", res.status_code, res.text)
        return False
    
    token = res.json().get('access_token')
    print("Login OK. Testando /auth/me...")
    
    me_res = requests.get(f"{URL}/auth/me", headers={'Authorization': f'Bearer {token}'})
    if me_res.status_code == 200:
        print("Success! /auth/me ->", me_res.json())
        return True
    else:
        print("Failed /auth/me:", me_res.status_code, me_res.text)
        return False

# Poll a few times if Render is still deploying
success = False
for i in range(10):
    if test_login_and_me():
        success = True
        break
    print("Waiting 10s for Render deployment...")
    time.sleep(10)

if success:
    print("ALL TESTS PASSED ON LIVE SERVER!")
else:
    print("RENDER MIGHT NOT BE DEPLOYED YET, OR THE BUG IS STILL THERE.")
