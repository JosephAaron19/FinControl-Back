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
        print("Success?")
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8')
    print("HTTP Code:", e.code)
    # Extract traceback info using regex or printing key lines
    # Search for <pre class="exception_value">...</pre>
    match = re.search(r'<pre class="exception_value">([^<]+)</pre>', body)
    if match:
         print("Exception Value:", match.group(1))
    
    # Let's extract the traceback lines
    match_tb = re.search(r'<textarea id="traceback_area"[^>]*>([^<]+)</textarea>', body)
    if match_tb:
         print("Traceback:\n", match_tb.group(1)[:2000])
    else:
         # Print first 2000 lines of body to see what we can find
         lines = body.split('\n')
         for line in lines[:100]:
             if 'exception' in line.lower() or 'error' in line.lower() or 'File' in line:
                 print(line.strip())
except Exception as e:
    print(e)
