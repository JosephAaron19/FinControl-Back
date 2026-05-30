import urllib.request
import json

def test_login(payload, name):
    print(f"\n--- Testing: {name} ---")
    req = urllib.request.Request(
        'http://127.0.0.1:8001/api/auth/login/',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as response:
            print("Status:", response.status)
            print("Body:", response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print("HTTP Error Status:", e.code)
        body = e.read().decode('utf-8')
        if e.code == 500:
             print("500 Error Body (first 1000 chars):")
             print(body[:1000])
             # Save full HTML to debug
             with open(f"debug_500_{name}.html", "w", encoding="utf-8") as f:
                 f.write(body)
             print(f"Full HTML traceback saved to debug_500_{name}.html")
        else:
             print("Error Body:", body)
    except Exception as e:
        print("Other Error:", e)

if __name__ == '__main__':
    # Test 1: Empty body
    test_login({}, "empty_body")
    # Test 2: Only username
    test_login({"dni": "70043709"}, "only_username")
    # Test 3: Username + password
    test_login({"dni": "70043709", "password": "wrong_password"}, "wrong_password")
    # Test 4: Username + password + origen=movil
    test_login({"dni": "70043709", "password": "wrong_password", "origen": "movil"}, "wrong_password_movil")
