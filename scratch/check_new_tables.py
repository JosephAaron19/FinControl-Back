import os
import django
import sys

sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from django.db import connection

tables = ['horarios', 'horario_detalles', 'usuario_horarios', 'intercambios_horario']

for table in tables:
    print(f"\n--- TABLA: {table} ---")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = 'finc' AND table_name = '{table}'")
        cols = cursor.fetchall()
        if not cols:
            # Try public or case-sensitive schema if not found in lowercase 'finc'
            cursor.execute(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table}'")
            cols = cursor.fetchall()
            
        for row in cols:
            print(f"COL: {row[0]} | TYPE: {row[1]} | NULL: {row[2]}")
