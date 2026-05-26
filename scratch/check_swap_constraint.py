import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'chk_intercambios_horario_estado'")
    row = cursor.fetchone()
    if row:
        print("Constraint definition:", row[0])
    else:
        print("Constraint not found.")
