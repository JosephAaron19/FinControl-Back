import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from django.db import connection

print("--- Inspecting jornada_actividades schema ---")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'jornada_actividades'
        ORDER BY ordinal_position;
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"Columna: {row[0]:<25} Tipo: {row[1]:<20} Nullable: {row[2]:<5}")

print("\n--- Inspecting table constraints ---")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = 'jornada_actividades'::regclass;
    """)
    for row in cursor.fetchall():
        print(f"Constraint: {row[0]:<40} Def: {row[1]}")
