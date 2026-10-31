import io
from urllib.parse import urlsplit
from django.http import HttpResponse,JsonResponse
import app as services
from .storage import connect

# One domain implementation shared by both verification environments.
services.connect=connect
handler=services.Application('postgresql')

class OriginMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.method=='POST':
            origin=request.headers.get('Origin')
            if origin and urlsplit(origin).netloc!=request.get_host():return JsonResponse({'error':'Origen no autorizado'},status=403)
            if request.content_type!='application/json':return JsonResponse({'error':'Se requiere application/json'},status=415)
        return self.get_response(request)

def gateway(request):
    if len(request.body)>16384:return JsonResponse({'error':'Solicitud demasiado grande'},status=413)
    env={'PATH_INFO':request.path,'REQUEST_METHOD':request.method,'QUERY_STRING':request.META.get('QUERY_STRING',''),'CONTENT_LENGTH':str(len(request.body)),'wsgi.input':io.BytesIO(request.body),'HTTP_COOKIE':request.META.get('HTTP_COOKIE',''),'HTTP_X_CSRF_TOKEN':request.headers.get('X-CSRF-Token',''),'REMOTE_ADDR':request.META.get('REMOTE_ADDR','local')}
    got={}
    def start(status,headers):got['status']=int(status.split()[0]);got['headers']=headers
    body=b''.join(handler(env,start));response=HttpResponse(body,status=got['status'])
    for k,v in got['headers']:
        if k=='Set-Cookie':response.cookies.load(v)
        else:response[k]=v
    return response
