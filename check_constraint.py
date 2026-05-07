from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'historial_jornadas_estado_jornada_check'")
    for row in cursor.fetchall():
        print(row[0])
