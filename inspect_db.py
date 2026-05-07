from django.db import connection
tables = ['configuracion_tracking', 'ubicacion_puntos']
for table in tables:
    print(f"\n--- TABLA: {table} ---")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'finc' AND table_name = '{table}'")
        for row in cursor.fetchall():
            print(f"COL: {row[0]} | TYPE: {row[1]}")
