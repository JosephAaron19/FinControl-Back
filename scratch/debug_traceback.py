import os
import sys
import django
import traceback

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.serializers import CustomTokenObtainPairSerializer

def test_login(dni, password):
    print(f"\n--- Traceback for DNI: {dni} ---")
    serializer = CustomTokenObtainPairSerializer(data={
        'dni': dni,
        'password': password,
        'origen': 'movil'
    })
    
    if serializer.is_valid():
        try:
            validated_data = serializer.validate(serializer.validated_data)
        except Exception as e:
            traceback.print_exc()
    else:
        print(f"Serializer errors: {serializer.errors}")

test_login('prueba', '123456')
