import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ACTHA_kasir.settings')

from ACTHA_kasir.wsgi import application

app = application
