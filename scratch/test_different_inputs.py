import urllib.request
import json

def test_login(payload, name):
    req = urllib.request.Request(
        'http://127.0.0.1:8001/api/auth/login/',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as response:
            print(f"{name}: Success - Status: {response.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"{name}: HTTP Error {e.code} - Body: {body[:150]}")
    except Exception as e:
        print(f"{name}: Other Error: {e}")

if __name__ == '__main__':
    test_login({"dni": "70043709", "password": "123456", "origen": "movil"}, "1. valid_assessor_movil")
    test_login({"dni": "admin", "password": "123456", "origen": "movil"}, "2. admin_movil")
    test_login({"dni": "admin", "password": "123456", "origen": "web"}, "3. admin_web")
    test_login({"dni": "nonexistent", "password": "wrong", "origen": "movil"}, "4. nonexistent_movil")
    test_login({"dni": "70043709", "password": "wrong", "origen": "movil"}, "5. wrong_password_movil")
    test_login({"username": "70043709", "password": "123456"}, "6. username_only")
    test_login({"dni": "Prueba", "password": "123456", "origen": "movil"}, "7. Prueba_capitalized_movil")
    test_login({"dni": "prueba", "password": "123456", "origen": "movil"}, "8. prueba_lowercase_movil")
