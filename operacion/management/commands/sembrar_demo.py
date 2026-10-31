import os
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from operacion.storage import connect
from app import password_hash,mutate

def seed_accounts(db,password):
    for aq in ['SIM-A','SIM-B']:
        db.execute('INSERT INTO acueducto VALUES(?,?)',(aq,'Acueducto ficticio '+aq))
        for role in ['admin','operador','consulta']:
            db.execute('INSERT INTO cuenta(aq,login,hash,rol,exportar) VALUES(?,?,?,?,?)',(aq,aq.lower()+'-'+role,password_hash(password),role,int(role=='admin')))

class Command(BaseCommand):
    help='Carga exclusivamente dos organizaciones ficticias; no sobrescribe registros.'
    def handle(self,*args,**options):
        password=os.environ.get('DEMO_PASSWORD','')
        if len(password)<12:raise CommandError('Falta DEMO_PASSWORD de al menos 12 caracteres')
        db=connect()
        if db.execute('SELECT COUNT(*) FROM acueducto').fetchone()[0]:
            self.stdout.write('Datos existentes conservados; no se repite la siembra.');return
        with transaction.atomic():
            seed_accounts(db,password)
            for aq in ['SIM-A','SIM-B']:
                actor=dict(db.execute("SELECT * FROM cuenta WHERE aq=? AND rol='operador'",(aq,)).fetchone())
                for j in range(1,9):
                    u=mutate(db,actor,'usuario',{'codigo':f'U{j:03d}'})['id']
                    p=mutate(db,actor,'predio',{'codigo':f'P{j:03d}','usuario':u})['id']
                    m=mutate(db,actor,'medidor',{'serial':f'{aq}-M{j:03d}'})['id']
                    i=mutate(db,actor,'instalacion',{'predio':p,'medidor':m,'inicio':'2026-01-01T00:00:00Z'})['id']
                    for month,value in [(2,'100.000'),(3,'112.250'),(4,'124.500')]:
                        mutate(db,actor,'lectura',{'instalacion':i,'fecha':f'2026-{month:02d}-01T00:00:00Z','valor':value})
                mutate(db,actor,'novedad',{'descripcion':'Ensayo sintético de baja presión; no corresponde a un evento real'})
        self.stdout.write('Creados 2 acueductos ficticios, 6 cuentas, 16 usuarios y 48 lecturas, con auditoría. No son observaciones de campo.')
