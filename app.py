"""Prototipo académico local. Solo datos sintéticos. Python estándar + SQLite.
No desplegar el servidor de referencia WSGI en Internet.
"""
import argparse
import csv
import getpass
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from http.cookies import SimpleCookie
from wsgiref.simple_server import make_server

ROOT=Path(__file__).resolve().parent
VERSION='0.2.0-simulacion'

class Error(Exception):
    def __init__(self,message,status=400):
        self.status=status
        super().__init__(message)

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def instant(value):
    try:
        d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if d.tzinfo is None: raise ValueError()
        return d.astimezone(timezone.utc).isoformat(timespec='seconds')
    except (ValueError,TypeError): raise Error('Fecha inválida; incluye hora y zona horaria')

def milli(value):
    try:
        n=Decimal(str(value))
        if not n.is_finite() or n<0 or n>Decimal('99999999999.999') or n.as_tuple().exponent < -3: raise ValueError()
        return int(n*1000)
    except (InvalidOperation,ValueError,TypeError): raise Error('Lectura no negativa, finita y con máximo tres decimales')

def text(value,minimum=1,maximum=200):
    v=str(value or '').strip()
    if not minimum<=len(v)<=maximum: raise Error(f'Texto requerido entre {minimum} y {maximum} caracteres')
    return v

def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),260000).hex()
    return salt+'$'+digest

def password_ok(password,encoded):
    return hmac.compare_digest(password_hash(password,encoded.split('$')[0]),encoded)

class LocalConnection(sqlite3.Connection):
    def __exit__(self,*args):
        try:return super().__exit__(*args)
        finally:self.close()

def connect(path):
    db=sqlite3.connect(path,timeout=10,factory=LocalConnection)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def initialize(path,password):
    if len(password)<12: raise Error('Usa al menos 12 caracteres para las cuentas sintéticas')
    path=Path(path)
    if path.exists(): raise Error('La base ya existe; no se sobrescribe')
    path.parent.mkdir(parents=True,exist_ok=True)
    db=connect(path)
    db.executescript((ROOT/'schema.sql').read_text(encoding='utf-8'))
    with db:
        for aq,label in [('SIM-A','Acueducto ficticio A'),('SIM-B','Acueducto ficticio B')]:
            db.execute('INSERT INTO acueducto VALUES(?,?)',(aq,label))
            for rol in ['admin','operador','consulta']:
                db.execute('INSERT INTO cuenta(aq,login,hash,rol,exportar) VALUES(?,?,?,?,?)',(aq,aq.lower()+'-'+rol,password_hash(password),rol,int(rol=='admin')))
    db.close()

def audit(db,actor,entity,key,action,before,after,reason):
    db.execute('INSERT INTO auditoria(aq,actor,instante,entidad,registro,accion,anterior,posterior,motivo) VALUES(?,?,?,?,?,?,?,?,?)',(actor['aq'],actor['id'],now(),entity,key,action,json.dumps(before,ensure_ascii=False) if before is not None else None,json.dumps(after,ensure_ascii=False) if after is not None else None,text(reason,3,500)))

def scope(db,actor,table,key):
    if table not in ['usuario','predio','medidor','instalacion','lectura','novedad','cuenta']: raise Error('Entidad inválida')
    row=db.execute(f'SELECT * FROM {table} WHERE id=? AND aq=?',(key,actor['aq'])).fetchone()
    if row is None: raise Error('Registro no disponible en tu acueducto',404)
    return dict(row)

def permit(actor,admin=False):
    if actor['rol'] not in (['admin'] if admin else ['admin','operador']): raise Error('Permiso denegado',403)

def consumptions(db,aq):
    rows=db.execute('SELECT l.*,m.serial,p.codigo predio,u.codigo usuario FROM lectura l JOIN instalacion i ON i.id=l.instalacion AND i.aq=l.aq JOIN medidor m ON m.id=i.medidor AND m.aq=i.aq JOIN predio p ON p.id=i.predio AND p.aq=i.aq JOIN usuario u ON u.id=p.usuario AND u.aq=p.aq WHERE l.aq=? ORDER BY l.instalacion,l.fecha',(aq,)).fetchall()
    previous={}; result=[]
    for row in rows:
        r=dict(row); prev=previous.get(r['instalacion'])
        r['consumo']=None
        r['desde']=None
        if r['estado']=='valida':
            if prev:
                r['consumo']=format(Decimal(r['valor']-prev['valor'])/1000,'.3f')
                r['desde']=prev['fecha']
            previous[r['instalacion']]=dict(row)
        r['valor']=format(Decimal(r['valor'])/1000,'.3f')
        result.append(r)
    return result

def state(db,actor):
    aq=actor['aq']
    data={'version':VERSION,'cuenta':{k:actor[k] for k in ['id','aq','login','rol','exportar']}}
    for table in ['usuario','predio','medidor','instalacion','novedad','auditoria']:
        data[table]=[dict(x) for x in db.execute(f'SELECT * FROM {table} WHERE aq=? ORDER BY id',(aq,))]
    data['lectura']=consumptions(db,aq)
    data['cuentas']=[{k:r[k] for k in ['id','login','rol','exportar']} for r in db.execute('SELECT * FROM cuenta WHERE aq=?',(aq,))] if actor['rol']=='admin' else []
    data['total_consumo']=format(sum((Decimal(r['consumo']) for r in data['lectura'] if r['consumo'] is not None),Decimal(0)),'.3f')
    return data

def mutate(db,actor,action,d):
    permit(actor,admin=action=='permisos')
    aq=actor['aq']; before=None
    if 'aq' in d and d['aq']!=aq: raise Error('No se admite cambiar de acueducto',403)
    reason=d.get('motivo','Registro de operación simulada')
    if action=='usuario':
        code=text(d.get('codigo'),1,50)
        key=db.execute('INSERT INTO usuario(aq,codigo) VALUES(?,?)',(aq,code)).lastrowid
        entity='usuario'
    elif action=='predio':
        u=scope(db,actor,'usuario',d.get('usuario'))
        key=db.execute('INSERT INTO predio(aq,codigo,usuario) VALUES(?,?,?)',(aq,text(d.get('codigo'),1,50),u['id'])).lastrowid
        entity='predio'
    elif action=='medidor':
        key=db.execute('INSERT INTO medidor(aq,serial) VALUES(?,?)',(aq,text(d.get('serial'),1,50))).lastrowid
        entity='medidor'
    elif action=='instalacion':
        p=scope(db,actor,'predio',d.get('predio')); m=scope(db,actor,'medidor',d.get('medidor'))
        start=instant(d.get('inicio'))
        if start>now(): raise Error('Inicio futuro no permitido en esta campaña')
        conflict=db.execute('SELECT 1 FROM instalacion WHERE aq=? AND (predio=? OR medidor=?) AND (fin IS NULL OR fin>?)',(aq,p['id'],m['id'],start)).fetchone()
        if conflict: raise Error('Existe una instalación con vigencia solapada')
        key=db.execute('INSERT INTO instalacion(aq,predio,medidor,inicio) VALUES(?,?,?,?)',(aq,p['id'],m['id'],start)).lastrowid
        entity='instalacion'
    elif action=='cerrar_instalacion':
        before=scope(db,actor,'instalacion',d.get('id')); end=instant(d.get('fin'))
        if before['fin'] or end<=before['inicio'] or end>now(): raise Error('Fin de instalación inválido')
        last=db.execute('SELECT MAX(fecha) FROM lectura WHERE instalacion=?',(before['id'],)).fetchone()[0]
        if last and end<=last: raise Error('El cierre debe ser posterior a todas las lecturas')
        key=before['id']; entity='instalacion'
        db.execute('UPDATE instalacion SET fin=? WHERE id=?',(end,key)); reason=text(d.get('motivo'),3,500)
    elif action=='lectura':
        inst=scope(db,actor,'instalacion',d.get('instalacion')); date=instant(d.get('fecha')); value=milli(d.get('valor'))
        if date<inst['inicio'] or (inst['fin'] and date>=inst['fin']) or date>now(): raise Error('Lectura fuera de vigencia o futura')
        last=db.execute('SELECT * FROM lectura WHERE instalacion=? ORDER BY fecha DESC LIMIT 1',(inst['id'],)).fetchone()
        if last and date<=last['fecha']: raise Error('Se requiere una fecha posterior a la última lectura')
        prev=db.execute("SELECT valor FROM lectura WHERE instalacion=? AND estado='valida' ORDER BY fecha DESC LIMIT 1",(inst['id'],)).fetchone()
        status='pendiente' if prev and value<prev['valor'] else 'valida'
        key=db.execute('INSERT INTO lectura(aq,instalacion,fecha,valor,estado) VALUES(?,?,?,?,?)',(aq,inst['id'],date,value,status)).lastrowid
        entity='lectura'
    elif action=='corregir_lectura':
        before=scope(db,actor,'lectura',d.get('id')); value=milli(d.get('valor')); status=d.get('estado')
        if status not in ['valida','descartada']: raise Error('Resolución inválida')
        if status=='valida':
            low=db.execute("SELECT valor FROM lectura WHERE instalacion=? AND fecha<? AND estado='valida' ORDER BY fecha DESC LIMIT 1",(before['instalacion'],before['fecha'])).fetchone()
            high=db.execute("SELECT valor FROM lectura WHERE instalacion=? AND fecha>? AND estado='valida' ORDER BY fecha LIMIT 1",(before['instalacion'],before['fecha'])).fetchone()
            if (low and value<low['valor']) or (high and value>high['valor']): raise Error('La corrección rompe el orden de la serie')
        key=before['id']; entity='lectura'; reason=text(d.get('motivo'),3,500)
        db.execute('UPDATE lectura SET valor=?,estado=? WHERE id=?',(value,status,key))
    elif action=='novedad':
        key=db.execute("INSERT INTO novedad(aq,descripcion,estado,apertura) VALUES(?,?,'abierta',?)",(aq,text(d.get('descripcion'),10,500),now())).lastrowid
        entity='novedad'
    elif action=='estado_novedad':
        before=scope(db,actor,'novedad',d.get('id')); target=d.get('estado')
        if (before['estado'],target) not in [('abierta','en gestion'),('en gestion','cerrada')]: raise Error('Transición no permitida')
        reason=text(d.get('motivo'),3,500); key=before['id']; entity='novedad'
        db.execute('UPDATE novedad SET estado=?,cierre=?,motivo=? WHERE id=?',(target,now() if target=='cerrada' else None,reason,key))
    elif action=='permisos':
        row=scope(db,actor,'cuenta',d.get('id')); key=row['id']; entity='cuenta'
        before={k:row[k] for k in ['id','rol','exportar']}
        if d.get('rol') not in ['admin','operador','consulta'] or type(d.get('exportar')) is not bool: raise Error('Rol o permiso inválido')
        if key==actor['id'] and d['rol']!='admin': raise Error('No puedes retirar tu propia administración')
        db.execute('UPDATE cuenta SET rol=?,exportar=? WHERE id=?',(d['rol'],int(d['exportar']),key)); reason=text(d.get('motivo'),3,500)
    else: raise Error('Operación no disponible',404)
    after=scope(db,actor,entity,key)
    if entity=='cuenta': after={k:after[k] for k in ['id','rol','exportar']}
    audit(db,actor,entity,key,action,before,after,reason)
    return {'id':key,'entidad':entity,'estado':after.get('estado')}

class Application:
    def __init__(self,path): self.path=Path(path); self.failures={}
    def __call__(self,env,start_response):
        headers=[('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Referrer-Policy','same-origin'),('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")]
        content_type='application/json; charset=utf-8'; code=200
        db=None
        try:
            route=env['PATH_INFO']; method=env['REQUEST_METHOD']
            if route in ['/','/ui.js','/styles.css'] and method=='GET':
                name={'/':'index.html','/ui.js':'ui.js','/styles.css':'styles.css'}[route]
                content_type={'/':'text/html; charset=utf-8','/ui.js':'text/javascript; charset=utf-8','/styles.css':'text/css; charset=utf-8'}[route]
                body=(ROOT/name).read_bytes()
            else:
                db=connect(self.path)
                length=int(env.get('CONTENT_LENGTH') or 0)
                if length>16384: raise Error('Solicitud demasiado grande',413)
                d=json.loads(env['wsgi.input'].read(length) or b'{}') if method=='POST' else {}
                if not isinstance(d,dict): raise Error('Se requiere un objeto JSON')
                if route=='/api/login' and method=='POST':
                    login=text(d.get('login'),1,80); t=time.time(); key=(env.get('REMOTE_ADDR','local'),login)
                    recent=[x for x in self.failures.get(key,[]) if t-x<60]
                    if len(recent)>=8: raise Error('Espera un minuto antes de reintentar',429)
                    row=db.execute('SELECT * FROM cuenta WHERE login=? AND activo=1',(login,)).fetchone()
                    valid=password_ok(str(d.get('password','')),row['hash']) if row else password_ok('invalid',password_hash('dummy'))
                    if not row or not valid:
                        self.failures[key]=recent+[t]; raise Error('Credenciales inválidas',401)
                    token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24)
                    with db: db.execute('INSERT INTO sesion VALUES(?,?,?,?)',(token,row['id'],csrf,t+3600))
                    headers.append(('Set-Cookie',f'agua_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600'))
                    body=json.dumps({'csrf':csrf,'version':VERSION}).encode()
                else:
                    cookie=SimpleCookie(); cookie.load(env.get('HTTP_COOKIE',''))
                    token=cookie['agua_session'].value if 'agua_session' in cookie else ''
                    row=db.execute('SELECT c.*,s.csrf FROM sesion s JOIN cuenta c ON c.id=s.cuenta WHERE s.token=? AND s.expira>? AND c.activo=1',(token,time.time())).fetchone()
                    if not row: raise Error('Inicia sesión',401)
                    actor=dict(row)
                    if method=='POST' and not hmac.compare_digest(env.get('HTTP_X_CSRF_TOKEN',''),actor['csrf']): raise Error('Token de formulario inválido',403)
                    if route=='/api/state' and method=='GET': body=json.dumps({**state(db,actor),'csrf':actor['csrf']},ensure_ascii=False).encode('utf-8')
                    elif route=='/api/export' and method=='GET':
                        if not actor['exportar']: raise Error('Exportación no autorizada',403)
                        from urllib.parse import parse_qs
                        q=parse_qs(env.get('QUERY_STRING','')); aq=q.get('aq',[actor['aq']])[0]
                        if aq!=actor['aq']: raise Error('Exportación cruzada denegada',403)
                        rows=consumptions(db,actor['aq']); user=q.get('usuario',[''])[0]; month=q.get('mes',[''])[0]
                        rows=[r for r in rows if (not user or r['usuario']==user) and (not month or r['fecha'].startswith(month))]
                        out=io.StringIO(); w=csv.writer(out,delimiter=';'); w.writerow(['usuario','predio','medidor','fecha','lectura_m3','estado','desde','consumo_m3'])
                        for r in rows:
                            vals=[r[x] for x in ['usuario','predio','serial','fecha','valor','estado','desde','consumo']]
                            w.writerow([("'"+str(v)) if str(v or '').startswith(('=','+','-','@')) else v for v in vals])
                        body=('\ufeff'+out.getvalue()).encode('utf-8'); content_type='text/csv; charset=utf-8'
                        headers.append(('Content-Disposition','attachment; filename="lecturas_simuladas.csv"'))
                    elif route=='/api/logout' and method=='POST':
                        with db: db.execute('DELETE FROM sesion WHERE token=?',(token,))
                        headers.append(('Set-Cookie','agua_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')); body=b'{}'
                    elif route.startswith('/api/') and method=='POST':
                        with db: result=mutate(db,actor,route[5:],d)
                        body=json.dumps(result).encode()
                    else: raise Error('Recurso no disponible',404)
        except Error as e: code=e.status; body=json.dumps({'error':str(e)},ensure_ascii=False).encode('utf-8')
        except sqlite3.IntegrityError: code=400; body=json.dumps({'error':'Registro duplicado, referencia inválida o restricción de integridad'}).encode()
        except (ValueError,TypeError,KeyError): code=400; body=json.dumps({'error':'Solicitud inválida'}).encode()
        except Exception:
            code=500; body=json.dumps({'error':'Error interno; revisa el registro de ejecución local'}).encode()
            import traceback; traceback.print_exc()
        finally:
            if db: db.close()
        headers += [('Content-Type',content_type),('Content-Length',str(len(body)))]
        start_response(f'{code} '+{200:'OK',400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',413:'Too Large',429:'Too Many Requests',500:'Internal Server Error'}.get(code,'Error'),headers)
        return [body]

def backup(source,target):
    if Path(target).exists(): raise Error('La copia destino ya existe; no se sobrescribe')
    with connect(source) as src, connect(target) as dest: src.backup(dest)

def restore(source,target):
    if Path(target).exists(): raise Error('La restauración requiere un destino nuevo')
    backup(source,target)
    with connect(target) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone(): raise Error('Copia no íntegra')
        db.execute('DELETE FROM sesion')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--db',default=str(ROOT/'datos'/'simulacion.sqlite3')); p.add_argument('--port',type=int,default=8086); p.add_argument('--init',action='store_true'); p.add_argument('--backup'); p.add_argument('--restore-from'); args=p.parse_args()
    if args.init:
        initialize(args.db,getpass.getpass('Clave de las seis cuentas ficticias (12 o más caracteres): '))
        print('Base sintética creada. Cuentas: sim-a-admin, sim-a-operador, sim-a-consulta; equivalentes sim-b. Inicia con python app.py')
    elif args.backup: backup(args.db,args.backup); print('Copia creada sin sobrescribir destinos')
    elif args.restore_from: restore(args.restore_from,args.db); print('Restauración íntegra en destino nuevo; sesiones cerradas')
    else:
        if not Path(args.db).exists(): raise SystemExit('Primero ejecuta python app.py --init')
        with make_server('127.0.0.1',args.port,Application(args.db)) as server:
            print(f'Agua Antioquia {VERSION}: http://127.0.0.1:{args.port} - datos ficticios',flush=True)
            server.serve_forever()
