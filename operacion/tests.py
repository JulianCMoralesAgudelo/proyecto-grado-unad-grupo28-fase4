import json
import sqlite3
from django.test import TestCase,Client
from django.db import transaction
from app import mutate
from operacion.storage import connect
from operacion.management.commands.sembrar_demo import seed_accounts

PASSWORD='ClaveExclusivaEnsayo2026!'

class IntegratedTests(TestCase):
    def setUp(self):
        self.db=connect();seed_accounts(self.db,PASSWORD)
        self.actor=dict(self.db.execute("SELECT * FROM cuenta WHERE login='sim-a-operador'").fetchone())
        self.client=Client();self.csrf=''
        self.login('sim-a-operador')
        self.u=self.post('usuario',{'codigo':'U001'})['id']
        self.p=self.post('predio',{'codigo':'P001','usuario':self.u})['id']
        self.m=self.post('medidor',{'serial':'M001'})['id']
        self.i=self.post('instalacion',{'predio':self.p,'medidor':self.m,'inicio':'2026-01-01T00:00:00Z'})['id']
        self.r=self.post('lectura',{'instalacion':self.i,'fecha':'2026-02-01T00:00:00Z','valor':'100.125'})['id']
    def login(self,name):
        r=self.client.post('/api/login',data=json.dumps({'login':name,'password':PASSWORD}),content_type='application/json');self.assertEqual(r.status_code,200);self.csrf=r.json()['csrf']
    def post(self,name,data,expected=200):
        r=self.client.post('/api/'+name,data=json.dumps(data),content_type='application/json',HTTP_X_CSRF_TOKEN=self.csrf);self.assertEqual(r.status_code,expected,r.content);return r.json()
    def reading(self,**kw):return {'instalacion':self.i,'fecha':'2026-03-01T00:00:00Z','valor':'115.375',**kw}
    def state(self):return self.client.get('/api/state').json()
    def test_consumption(self):
        self.post('lectura',self.reading());self.assertEqual(self.state()['lectura'][-1]['consumo'],'15.250')
    def test_decreasing_pending_and_audited_correction(self):
        r=self.post('lectura',self.reading(valor='99.000'));self.assertEqual(r['estado'],'pendiente');self.assertIsNone(self.state()['lectura'][-1]['consumo'])
        self.post('corregir_lectura',{'id':r['id'],'valor':'115.375','estado':'valida','motivo':'Corrección sintética documentada'});s=self.state();self.assertEqual(s['lectura'][-1]['consumo'],'15.250');self.assertEqual(json.loads(s['auditoria'][-1]['anterior'])['valor'],99000)
    def test_invalid_readings(self):
        for v in ['-1','NaN','1.0001']:self.post('lectura',self.reading(valor=v),400)
        self.post('lectura',self.reading(fecha='2026-02-30T00:00:00Z'),400)
    def test_duplicate(self):self.post('usuario',{'codigo':'U001'},400)
    def test_scope(self):
        self.post('usuario',{'codigo':'X','aq':'SIM-B'},403);self.login('sim-b-consulta');self.assertEqual(self.state()['usuario'],[])
    def test_consultation_cannot_write(self):
        self.login('sim-a-consulta');self.post('usuario',{'codigo':'X'},403);self.post('corregir_lectura',{'id':self.r,'valor':'100','estado':'valida','motivo':'Intento'},403)
    def test_export_permissions_and_total(self):
        self.post('lectura',self.reading());self.assertEqual(self.client.get('/api/export').status_code,403);self.login('sim-a-admin');r=self.client.get('/api/export?mes=2026-03&usuario=U001');self.assertEqual(r.status_code,200);self.assertIn('15.250',r.content.decode('utf-8-sig'));self.assertEqual(self.client.get('/api/export?aq=SIM-B').status_code,403)
    def test_csrf(self):
        r=self.client.post('/api/usuario',data=json.dumps({'codigo':'X'}),content_type='application/json');self.assertEqual(r.status_code,403)
    def test_cross_origin(self):
        r=self.client.post('/api/usuario',data=json.dumps({'codigo':'X'}),content_type='application/json',HTTP_X_CSRF_TOKEN=self.csrf,HTTP_ORIGIN='https://otro.example');self.assertEqual(r.status_code,403)
    def test_logout(self):self.post('logout',{});self.assertEqual(self.client.get('/api/state').status_code,401)
    def test_novelty_lifecycle(self):
        n=self.post('novedad',{'descripcion':'Baja presión simulada para la prueba'})['id'];self.post('estado_novedad',{'id':n,'estado':'cerrada','motivo':'Inválido'},400);self.post('estado_novedad',{'id':n,'estado':'en gestion','motivo':'Revisión'});self.post('estado_novedad',{'id':n,'estado':'cerrada','motivo':'Cierre documentado'});self.assertIsNotNone(self.state()['novedad'][0]['cierre'])
    def test_meter_replacement(self):
        self.post('cerrar_instalacion',{'id':self.i,'fin':'2026-03-01T00:00:00Z','motivo':'Reemplazo'});m=self.post('medidor',{'serial':'M002'})['id'];i=self.post('instalacion',{'predio':self.p,'medidor':m,'inicio':'2026-03-01T00:00:00Z'})['id'];self.post('lectura',{'instalacion':i,'fecha':'2026-04-01T00:00:00Z','valor':'1.000'});self.assertIsNone(self.state()['lectura'][-1]['consumo'])
    def test_audit_db_immutable(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with transaction.atomic():self.db.execute("UPDATE auditoria SET motivo='Inválido'")
    def test_postgres_cross_reference(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with transaction.atomic():self.db.execute("INSERT INTO predio(aq,codigo,usuario) VALUES('SIM-B','CRUCE',?)",(self.u,))
    def test_health_ui_and_hash_not_disclosed(self):
        self.assertEqual(self.client.get('/').status_code,200);body=json.dumps(self.state());self.assertNotIn('hash',body);self.assertNotIn(PASSWORD,body)
