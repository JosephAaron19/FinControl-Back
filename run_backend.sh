#!/bin/bash
# Script para iniciar el entorno y el backend de FinControl

# Ir al directorio del script
cd "$(dirname "$0")"

# Levantar base de datos en Docker si no está activa
if [ ! "$(docker ps -q -f name=fincontrol-db)" ]; then
    if [ "$(docker ps -aq -f name=fincontrol-db)" ]; then
        echo "Iniciando contenedor de base de datos existente..."
        docker start fincontrol-db
    else
        echo "Creando e iniciando nuevo contenedor de base de datos..."
        docker run --name fincontrol-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=postgres -p 5432:5432 -d postgres:latest
        echo "Esperando a que la base de datos esté lista..."
        until docker exec fincontrol-db pg_isready -U postgres >/dev/null 2>&1; do
            sleep 1
        done
        echo "Creando esquema 'finc'..."
        docker exec -i fincontrol-db psql -U postgres -c "CREATE SCHEMA IF NOT EXISTS finc;"
    fi
else
    echo "El contenedor de base de datos ya está corriendo."
fi

# Activar entorno virtual de Python
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: No se encontró el entorno virtual 'venv'. Ejecuta primero 'python3 -m venv venv' e instala las dependencias."
    exit 1
fi

# Iniciar servidor de desarrollo Django en puerto 8001
echo "Iniciando servidor backend en http://0.0.0.0:8001/ ..."
python manage.py runserver 0.0.0.0:8001
