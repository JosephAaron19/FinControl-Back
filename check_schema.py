from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name, is_nullable, data_type FROM information_schema.columns WHERE table_name = 'ubicacion_puntos'")
    for row in cursor.fetchall():
        print(row)
