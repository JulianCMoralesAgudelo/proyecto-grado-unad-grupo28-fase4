import os
SECRET_KEY=os.environ['SECRET_KEY']
DEBUG=False
ALLOWED_HOSTS=['localhost','127.0.0.1','testserver']
ROOT_URLCONF='proyecto.urls'
WSGI_APPLICATION='proyecto.wsgi.application'
INSTALLED_APPS=['operacion']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','operacion.views.OriginMiddleware']
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.environ.get('PGDATABASE','agua_simulada'),'HOST':os.environ.get('PGHOST','db'),'PORT':os.environ.get('PGPORT','5432'),'USER':os.environ.get('PGUSER','agua'),'PASSWORD':os.environ['PGPASSWORD']}}
LANGUAGE_CODE='es-co'
TIME_ZONE='America/Bogota'
USE_TZ=True
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY='same-origin'
DATA_UPLOAD_MAX_MEMORY_SIZE=16384
