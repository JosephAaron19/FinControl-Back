from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'finc'")
    for row in cursor.fetchall():
        print(row[0])
