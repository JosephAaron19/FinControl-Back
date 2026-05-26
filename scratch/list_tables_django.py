import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT pg_get_constraintdef(oid), conname FROM pg_constraint WHERE conrelid = 'finc.horario_detalles'::regclass")
    for row in cursor.fetchall():
        print(row)
