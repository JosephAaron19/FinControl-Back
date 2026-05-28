import os
import sys
import django

# Add the parent directory to the path so django settings can be loaded
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import UsuarioHorario
from datetime import date

# Update assignments starting tomorrow (which were created under UTC next-day shift) to start today
affected = UsuarioHorario.objects.filter(vigente_desde=date(2026, 5, 28))
count = affected.count()
for uh in affected:
    uh.vigente_desde = date(2026, 5, 27)
    uh.save()

print(f"Updated {count} UsuarioHorario records to start today (2026-05-27).")
