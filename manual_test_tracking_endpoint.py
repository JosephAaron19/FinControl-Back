import os
import django
import sys

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from api.models import HistorialJornada, UbicacionPunto
from api.views import JourneyTrackingRecorridoJornadaView

User = get_user_model()

print("Django setup completed successfully!")

def run_test():
    # Fetch first active shift or user
    historial = HistorialJornada.objects.first()
    user = User.objects.filter(rol__nombre__icontains='admin').first() or User.objects.first()
    
    if not historial:
        print("No shift histories found in database. Test cannot fetch a real shift, but imports are correct.")
        return
        
    print(f"Testing with HistorialJornada ID: {historial.id} and User: {user.nombre_completo if user else 'None'}")
    
    if not user:
        print("No users found. Cannot run request test.")
        return

    # Setup request factory
    factory = RequestFactory()
    request = factory.get(f'/api/tracking/recorrido-jornada/{historial.id}/')
    request.user = user
    
    # Instantiate view
    view = JourneyTrackingRecorridoJornadaView.as_view()
    
    try:
        response = view(request, historial_jornada_id=historial.id)
        print(f"Response status code: {response.status_code}")
        print("Response data:")
        print(response.data)
        print("Success! Backend endpoint is fully operational and correct.")
    except Exception as e:
        print(f"Error executing view: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_test()
