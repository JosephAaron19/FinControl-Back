import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.serializers import CustomTokenObtainPairSerializer

serializer = CustomTokenObtainPairSerializer(data={
    'dni': 'prueba',
    'password': '123456',
    'origen': 'movil'
})

if serializer.is_valid():
    print("Validated data keys:", list(serializer.validated_data.keys()))
    print("Validated data values:", serializer.validated_data)
else:
    print("Errors:", serializer.errors)
