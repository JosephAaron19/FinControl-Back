import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from django.db import connection

print("=== SCHEMAS IN REMOTE DATABASE ===")
with connection.cursor() as cursor:
    cursor.execute("SELECT schema_name FROM information_schema.schemata;")
    for row in cursor.fetchall():
        print(f"- Schema: {row[0]}")
        
print("\n=== TABLES IN REMOTE DATABASE ===")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name;
    """)
    for row in cursor.fetchall():
        print(f"- Schema: {row[0]} | Table: {row[1]}")
print("=================================")
