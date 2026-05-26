import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.serializers import CustomTokenObtainPairSerializer

def test_login(dni, password):
    print(f"\n--- Testing login for DNI: {dni} ---")
    serializer = CustomTokenObtainPairSerializer(data={
        'dni': dni,
        'password': password,
        'origen': 'movil'
    })
    
    if serializer.is_valid():
        try:
            validated_data = serializer.validate(serializer.validated_data)
            print("[SUCCESS] Login successful!")
            print(f"Tokens/Data returned: {validated_data}")
        except Exception as e:
            print(f"[ERROR during validate] {type(e).__name__}: {e}")
    else:
        print(f"[INVALID DATA] Serializer errors: {serializer.errors}")

test_login('prueba', '123456')
test_login('70043709', '123456')
