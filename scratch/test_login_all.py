import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.serializers import CustomTokenObtainPairSerializer

def run_login_test(dni, password):
    print(f"\n--- Testing DNI: {dni} | Password: {password} ---")
    serializer = CustomTokenObtainPairSerializer(data={
        'dni': dni,
        'password': password,
        'origen': 'movil'
    })
    
    if serializer.is_valid():
        print("[SUCCESS] Login successful!")
        print("Response Data:", serializer.validated_data)
    else:
        print("[ERROR 400] Validation failed!")
        print("Errors:", serializer.errors)

# Test 1: Active assessor with correct password
run_login_test('prueba', '123456')

# Test 2: Another active assessor
run_login_test('70043709', '123456')

# Test 3: Admin login (should be denied for mobile)
run_login_test('admin', '123456')

# Test 4: Incorrect password
run_login_test('prueba', 'wrong_password')
