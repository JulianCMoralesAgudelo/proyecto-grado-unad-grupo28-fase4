from django.urls import re_path
from operacion.views import gateway
urlpatterns=[re_path(r'^.*$',gateway)]
