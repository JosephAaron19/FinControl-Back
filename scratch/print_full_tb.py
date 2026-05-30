import urllib.request
import json
import re

req = urllib.request.Request(
    'http://127.0.0.1:8001/api/auth/login/',
    data=json.dumps({"username": "70043709", "password": "123456"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req) as response:
        print("Success")
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8')
    # Save the HTML to check the traceback
    with open("tb_500.html", "w", encoding="utf-8") as f:
         f.write(body)
    
    # Print lines containing "File " and surrounding lines to print the traceback
    lines = body.split('\n')
    in_tb = False
    for line in lines:
         if 'Traceback (most recent call ' in line or '<textarea id="traceback_area"' in line:
              in_tb = True
         if in_tb:
              print(line.strip())
         if in_tb and '</textarea>' in line:
              in_tb = False
except Exception as e:
    print(e)
