import os
import sys
import django
import traceback

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from api.views import CustomTokenObtainPairView

def run():
    factory = APIRequestFactory()
    data = {'dni': '70043709', 'password': '123456', 'origen': 'movil'}
    request = factory.post('/api/auth/login/', data, format='json')
    view = CustomTokenObtainPairView.as_view()

    try:
        response = view(request)
        print("Status Code:", response.status_code)
        print("Response:", response.data if hasattr(response, 'data') else None)
    except Exception as e:
        traceback.print_exc()

if __name__ == '__main__':
    run()
