import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:8001/api"
DNI = "admin"
PASSWORD = "123456"

def test_login_error():
    login_url = f"{BASE_URL}/auth/login/"
    login_data = json.dumps({"dni": DNI, "password": PASSWORD}).encode('utf-8')
    req = urllib.request.Request(
        login_url,
        data=login_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            print("Success!", response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print("HTTP Error Code:", e.code)
        print("Response Body:", e.read().decode('utf-8'))
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test_login_error()
