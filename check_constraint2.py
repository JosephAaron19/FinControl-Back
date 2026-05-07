from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'chk_ubicacion_puntos_origen'")
    for row in cursor.fetchall():
        print(row[0])
