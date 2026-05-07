from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT conname, pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE contype = 'c' AND conrelid = 'ubicacion_puntos'::regclass")
    for row in cursor.fetchall():
        print(row)
