import os
import sys
import django
import traceback

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from api.views import CustomTokenObtainPairView

def simulate_login(dni, password, origen=None):
    print(f"\n--- Simulating view login for DNI: {dni} ---")
    factory = APIRequestFactory()
    
    data = {'dni': dni, 'password': password}
    if origen:
         data['origen'] = origen
         
    request = factory.post('/api/auth/login/', data, format='json')
    view = CustomTokenObtainPairView.as_view()
    
    try:
        response = view(request)
        print(f"Status Code: {response.status_code}")
        print("Response Data:", response.data if hasattr(response, 'data') else None)
    except Exception as e:
        print("Exception caught in simulation:")
        traceback.print_exc()

if __name__ == '__main__':
    # Test with a user from the database
    simulate_login('70043709', '123456') # Let's see if 123456 is wrong or correct
    simulate_login('admin', '123456')
    simulate_login('70043709', 'wrong')
