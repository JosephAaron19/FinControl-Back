from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name, column_default FROM information_schema.columns WHERE table_name = 'ubicacion_puntos'")
    for row in cursor.fetchall():
        print(row)
