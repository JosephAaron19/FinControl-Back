import os
import sys
import django

# Add current working directory to path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from django.db import connection

settings = connection.settings_dict
print("=== ACTIVE DJANGO DATABASE CONNECTION SETTINGS ===")
print(f"Engine: {settings.get('ENGINE')}")
print(f"Database Name: {settings.get('NAME')}")
print(f"User: {settings.get('USER')}")
print(f"Host: {settings.get('HOST')}")
print(f"Port: {settings.get('PORT')}")
print(f"Options: {settings.get('OPTIONS')}")
print("==================================================")
