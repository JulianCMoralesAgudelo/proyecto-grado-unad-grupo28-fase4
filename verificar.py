"""Campaña reproducible del servidor y persistencia. No simula personas."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import shutil
import sqlite3
import tempfile
import time
from datetime import datetime,timezone
from app import Application,initialize,connect,backup,restore,VERSION

ROOT=Path(__file__).resolve().parent
EVID=ROOT.parent/'evidencias_fase4'
PASSWORD='ClaveSoloSintetica2026!'
RESULTS=[]

class Client:
    def __init__(self,path): self.app=Application(path); self.cookie=''; self.csrf=''
    def req(self,route,data=None,csrf=True):
        from urllib.parse import urlsplit
        p=urlsplit(route); raw=json.dumps(data).encode() if data is not None else b''
        env={'PATH_INFO':p.path,'QUERY_STRING':p.query,'REQUEST_METHOD':'POST' if data is not None else 'GET','CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),'HTTP_COOKIE':self.cookie,'HTTP_X_CSRF_TOKEN':self.csrf if csrf else '','REMOTE_ADDR':'127.0.0.1'}
        got={}
        def start(status,headers): got['status']=int(status.split()[0]);got['headers']=dict(headers)
        body=b''.join(self.app(env,start))
        if 'Set-Cookie' in got['headers']: self.cookie=got['headers']['Set-Cookie'].split(';')[0]
        try: b=json.loads(body)
        except (json.JSONDecodeError,UnicodeDecodeError): b=body.decode('utf-8-sig')
        if isinstance(b,dict) and 'csrf' in b:self.csrf=b['csrf']
        return got['status'],b
    def login(self,login):
        status,b=self.req('/api/login',{'login':login,'password':PASSWORD}); assert status==200,(status,b)
    def post(self,name,d,expected=200):
        s,b=self.req('/api/'+name,d); assert s==expected,(name,s,b); return b
    def state(self):
        s,b=self.req('/api/state');assert s==200;return b

def actor(db,login='sim-a-operador'):return dict(db.execute('SELECT * FROM cuenta WHERE login=?',(login,)).fetchone())

def build_series(c,code='U001'):
    u=c.post('usuario',{'codigo':code})['id']
    p=c.post('predio',{'codigo':'P'+code,'usuario':u})['id']
    m=c.post('medidor',{'serial':'M'+code})['id']
    i=c.post('instalacion',{'predio':p,'medidor':m,'inicio':'2026-01-01T00:00:00Z'})['id']
    r=c.post('lectura',{'instalacion':i,'fecha':'2026-02-01T00:00:00Z','valor':'100.125'})['id']
    return u,p,m,i,r

def check(cp,c,path,ids):
    u,p,m,i,r=ids
    reading=lambda **kw:{'instalacion':i,'fecha':'2026-03-01T00:00:00Z','valor':'115.375',**kw}
    if cp in ['CP01a','CP14b']:
        c.post('usuario',{'codigo':'X','aq':'SIM-B'},403)
    elif cp=='CP02a':c.post('usuario',{'codigo':'U001'},400)
    elif cp=='CP03a':
        n=c.post('predio',{'codigo':'OTRO','usuario':u});assert n['id']
    elif cp=='CP03b':
        other=Client(path);other.login('sim-b-operador');foreign=other.post('usuario',{'codigo':'EXTERNO'})['id'];c.post('predio',{'codigo':'CRUCE','usuario':foreign},404)
    elif cp=='CP04a':
        c.post('cerrar_instalacion',{'id':i,'fin':'2026-03-01T00:00:00Z','motivo':'Reemplazo sintético'})
        m2=c.post('medidor',{'serial':'REEMPLAZO'})['id'];i2=c.post('instalacion',{'predio':p,'medidor':m2,'inicio':'2026-03-01T00:00:00Z'})['id']
        c.post('lectura',{'instalacion':i2,'fecha':'2026-04-01T00:00:00Z','valor':'1.000'})
        rows=c.state()['lectura'];assert len(rows)==2 and all(x['consumo'] is None for x in rows)
    elif cp=='CP05a':c.post('lectura',reading(valor='-1'),400)
    elif cp=='CP05b':
        c.post('lectura',reading(fecha='2026-02-30T00:00:00Z'),400);c.post('lectura',reading(fecha='2025-12-31T00:00:00Z'),400)
    elif cp=='CP05c':
        b=c.post('lectura',reading(valor='99.000'));assert b['estado']=='pendiente';assert c.state()['lectura'][-1]['consumo'] is None
    elif cp=='CP05d':c.post('lectura',reading(instalacion=999999),404)
    elif cp=='CP05e':assert c.post('lectura',reading())['estado']=='valida'
    elif cp=='CP05f':
        x=c.post('lectura',reading(valor='99.000'))['id'];c.post('corregir_lectura',{'id':x,'valor':'115.375','estado':'valida','motivo':'Corrección de dato sintético'})
        s=c.state();assert s['lectura'][-1]['consumo']=='15.250';assert json.loads(s['auditoria'][-1]['anterior'])['valor']==99000
    elif cp=='CP06a':
        c.post('lectura',reading());assert c.state()['lectura'][-1]['consumo']=='15.250'
    elif cp=='CP07a':
        c.post('lectura',reading());row=c.state()['lectura'][-1];assert row['usuario']=='U001' and row['desde'].startswith('2026-02') and row['serial']=='MU001'
    elif cp=='CP08a':
        n=c.post('novedad',{'descripcion':'Baja presión simulada en sector de ensayo'})['id'];c.post('estado_novedad',{'id':n,'estado':'cerrada','motivo':'Intento inválido'},400)
        c.post('estado_novedad',{'id':n,'estado':'en gestion','motivo':'Revisión técnica simulada'});c.post('estado_novedad',{'id':n,'estado':'cerrada','motivo':''},400);c.post('estado_novedad',{'id':n,'estado':'cerrada','motivo':'Cierre técnico simulado'});assert c.state()['novedad'][0]['cierre']
    elif cp in ['CP10a','CP10b']:
        c.post('lectura',reading());c.login('sim-a-admin');status,b=c.req('/api/export?usuario=U001&mes=2026-03');assert status==200
        rows=list(csv.DictReader(io.StringIO(b),delimiter=';'));assert len(rows)==1 and rows[0]['consumo_m3']=='15.250';assert c.state()['total_consumo']=='15.250'
    elif cp=='CP10c':
        c.login('sim-a-consulta');assert c.req('/api/export')[0]==403
    elif cp=='CP11a':
        c.post('corregir_lectura',{'id':r,'valor':'100.000','estado':'valida','motivo':'Ajuste de línea base sintética'});s=c.state();a=s['auditoria'][-1];assert json.loads(a['anterior'])['valor']==100125 and json.loads(a['posterior'])['valor']==100000 and a['actor']
    elif cp in ['CP11b','CP12i']:
        c.login('sim-a-admin');c.post('auditoria',{'id':1,'motivo':'No permitido'},404)
        with connect(path) as db:
            try: db.execute("UPDATE auditoria SET motivo='Cambio' WHERE id=1")
            except sqlite3.IntegrityError: pass
            else: raise AssertionError('Auditoría mutable')
    elif cp in ['CP12a','CP12b','CP12c','CP12d']:
        c.login('sim-a-consulta');actions={'CP12a':('usuario',{'codigo':'PROHIBIDO'}),'CP12b':('corregir_lectura',{'id':r,'valor':'100','estado':'valida','motivo':'No permitido'}),'CP12c':('eliminar',{'id':r}),'CP12d':('corregir_lectura',{'id':r,'valor':'100','estado':'valida','motivo':'No permitido'})};action,data=actions[cp];c.post(action,data,403)
    elif cp=='CP12e':c.post('usuario',{'codigo':'OPERADOR-PERMITIDO'})
    elif cp=='CP12f':c.post('corregir_lectura',{'id':r,'valor':'100.125','estado':'valida','motivo':'Validación operativa simulada'})
    elif cp=='CP12g':c.post('permisos',{'id':1,'rol':'admin','exportar':True,'motivo':'Escalada no permitida'},403)
    elif cp=='CP12h':
        c.login('sim-a-admin');account=next(x for x in c.state()['cuentas'] if x['rol']=='consulta');c.post('permisos',{'id':account['id'],'rol':'consulta','exportar':True,'motivo':'Exportación de ensayo autorizada'});c.login('sim-a-consulta');assert c.req('/api/export')[0]==200
    elif cp=='CP13a':
        anonymous=Client(path);assert anonymous.req('/api/state')[0]==401
    elif cp=='CP13b':
        c.cookie='agua_session=invalid';assert c.req('/api/state')[0]==401
    elif cp=='CP13c':
        with connect(path) as db:db.execute('UPDATE sesion SET expira=0')
        assert c.req('/api/state')[0]==401
    elif cp=='CP14a':
        c.login('sim-b-consulta');s=c.state();assert not s['usuario'] and not s['lectura'] and not s['auditoria']
    elif cp=='CP14c':
        c.login('sim-a-admin');assert c.req('/api/export?aq=SIM-B')[0]==403
    elif cp in ['CP15a','CP15b','CP15c']:
        with connect(path) as db:
            if cp=='CP15a':sql="INSERT INTO usuario(aq,codigo) VALUES('SIM-A','U001')"
            elif cp=='CP15b':sql="INSERT INTO predio(aq,codigo,usuario) VALUES('SIM-A','INV',99999)"
            else:sql=f"INSERT INTO predio(aq,codigo,usuario) VALUES('SIM-B','INV',{u})"
            try:db.execute(sql)
            except sqlite3.IntegrityError:pass
            else:raise AssertionError('Restricción no aplicada')
    elif cp=='CP16a':
        # Prior limits: 100 serial WSGI requests, p95<=1000 ms, no errors.
        elapsed=[]
        for _ in range(100):
            t=time.perf_counter();c.state();elapsed.append(1000*(time.perf_counter()-t))
        p95=sorted(elapsed)[math.ceil(.95*len(elapsed))-1];assert p95<=1000
        return {'n':100,'modo':'WSGI serial sin red','p95_ms':p95,'mediana_ms':sorted(elapsed)[49],'limite_p95_ms':1000,'errores':0,'volumen':'1 usuario, 1 medidor, 1 lectura; microensayo, no carga operativa'}
    elif cp=='CP17a':
        # Short technical observation: not a statement of service availability.
        start=time.perf_counter();ok=0;attempts=20
        for _ in range(attempts):
            ok+=int(c.req('/api/state')[0]==200);time.sleep(.05)
        window=time.perf_counter()-start;assert ok==attempts
        return {'intentos':attempts,'respuestas_ok':ok,'ventana_s':window,'intervalo_objetivo_s':.05,'meta':'20/20 respuestas','alcance':'Observación corta WSGI; no mide disponibilidad operativa temporal CP17'}
    elif cp=='CP19a':
        dest=Path(path).with_name('copia.sqlite3');target=Path(path).with_name('restaurada.sqlite3')
        mark=time.time();backup(path,dest);c.post('usuario',{'codigo':'POSTERIOR-COPIA'});incident=time.time();start=time.perf_counter();restore(dest,target);rto=time.perf_counter()-start
        with connect(dest) as original,connect(target) as restored:
            for table in ['usuario','predio','medidor','instalacion','lectura','novedad','auditoria']:
                assert original.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()==restored.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
            assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert restored.execute('PRAGMA foreign_key_check').fetchone() is None;assert restored.execute('SELECT COUNT(*) FROM sesion').fetchone()[0]==0
        assert rto<=30 and incident-mark<=60
        return {'RTO_s':rto,'RPO_s_cota_superior':incident-mark,'meta_RTO_s':30,'meta_RPO_s':60,'simulacion':'Incidente inmediatamente posterior al respaldo; transacción posterior ausente en copia; comparación de siete tablas e integridad'}
    else: raise AssertionError('Caso sin implementar: '+cp)
    return {'observado':'Se cumplieron las aserciones del procedimiento; datos sintéticos, servidor y SQLite'}

def main():
    EVID.mkdir(exist_ok=True)
    digest=hashlib.sha256()
    for f in sorted(ROOT.rglob('*')):
        if f.is_file() and not any(x in f.parts for x in ['datos','__pycache__']) and f.suffix in ['.py','.sql','.js','.html','.css','.yaml','.txt'] and f.name!='credenciales_locales.txt':
            digest.update(f.relative_to(ROOT).as_posix().encode());digest.update(f.read_bytes())
    fingerprint=digest.hexdigest()
    counts={1:1,2:1,3:2,4:1,5:6,6:1,7:1,8:1,9:2,10:3,11:2,12:9,13:3,14:3,15:3,16:1,17:1,18:1,19:1}
    with tempfile.TemporaryDirectory(prefix='agua_fase4_',dir=EVID) as tmp:
        base=Path(tmp)/'base.sqlite3';initialize(base,PASSWORD)
        c=Client(base);c.login('sim-a-operador');ids=build_series(c)
        for n,count in counts.items():
            for j in range(count):
                cp=f'CP{n:02d}{chr(97+j)}';row={'variante':cp,'obligatoria':n!=9,'fecha_utc':now_utc(),'version':VERSION,'sha256_fuente':fingerprint,'ejecutor':'verificador automatizado; no participante de acueducto','estado':'no ejecutado'}
                if n==9: row.update(estado='fuera de alcance',observado='RF-09 excluido del mínimo antes de campaña')
                elif n==18:row.update(estado='bloqueado',observado='Requiere tareas humanas M01; no se sustituyen personas por un programa')
                else:
                    work=Path(tmp)/cp;work.mkdir();dbpath=work/'ensayo.sqlite3';shutil.copy2(base,dbpath);client=Client(dbpath);client.login('sim-a-operador')
                    try:
                        detail=check(cp,client,dbpath,ids);row.update(estado='aprobado',detalle=detail)
                        if n==17:row.update(estado='bloqueado',observado='Microensayo técnico satisfactorio; falta ventana y medición temporal suficiente de disponibilidad')
                    except Exception as e:row.update(estado='fallido',observado=f'{type(e).__name__}: {e}')
                RESULTS.append(row)
        # Supplemental CSRF and logout checks, separate from the fixed denominator.
        client=Client(base);client.login('sim-a-operador');assert client.req('/api/usuario',{'codigo':'CSRF'},csrf=False)[0]==403
        client.post('logout',{});assert client.req('/api/state')[0]==401
    payload={'entorno':{'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'sistema':platform.platform(),'alcance':'Pruebas integradas WSGI + persistencia local; sin navegador en esta campaña'},'version':VERSION,'sha256_fuente':fingerprint,'pruebas':RESULTS,'adicionales':{'csrf_sin_token':'denegado','logout':'sesion_invalidada'}}
    (EVID/'campana_integrada.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    with (EVID/'campana_integrada.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['variante','obligatoria','estado','fecha_utc','evidencia','observado'])
        for r in RESULTS:w.writerow([r['variante'],r['obligatoria'],r['estado'],r['fecha_utc'],'campana_integrada.json#'+r['variante'],r.get('observado',json.dumps(r.get('detalle'),ensure_ascii=False))])
    summary={s:sum(r['estado']==s for r in RESULTS) for s in sorted(set(r['estado'] for r in RESULTS))}
    print(json.dumps({'resumen':summary,'variantes':len(RESULTS),'obligatorias':41,'sha256':fingerprint},ensure_ascii=False))
    if summary.get('fallido'):raise SystemExit(1)

def now_utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')
if __name__=='__main__':main()
