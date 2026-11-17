import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


SOURCES={
    'medata-pequenos': {
        'nombre':'Suscriptores y consumos de pequeños prestadores',
        'entidad':'Alcaldía de Medellín - MEData',
        'url':'https://medata.app.medellin.gov.co/node/16495',
        'licencia':'CC BY-SA 4.0',
        'granularidad':'Prestador, servicio, período, comuna y estrato/uso; cifras agregadas.',
        'actualizacion':'2025-02-01',
    },
    'medata-gran-prestador': {
        'nombre':'Suscriptores y consumos del gran prestador',
        'entidad':'Alcaldía de Medellín - MEData',
        'url':'https://medata.app.medellin.gov.co/node/16494',
        'licencia':'CC BY-SA 4.0',
        'granularidad':'Prestador, servicio, período y estrato/uso; cifras agregadas.',
        'actualizacion':'2025-02-01',
    },
    'medata-cobertura': {
        'nombre':'Reporte de estratificación y cobertura',
        'entidad':'Alcaldía de Medellín - MEData',
        'url':'https://medata.app.medellin.gov.co/node/16530',
        'licencia':'CC BY-SA 4.0',
        'granularidad':'Servicio, comuna, período y estrato; cifras agregadas.',
        'actualizacion':'2021-08-10',
    },
    'socrata-interrupciones': {
        'nombre':'Interrupciones programadas del servicio de acueducto',
        'entidad':'E.S.P. Empresas Públicas de Medellín - EPM, Antioquia',
        'url':'https://www.datos.gov.co/d/r9fv-awbc',
        'licencia':'CC BY-SA 4.0',
        'granularidad':'Una interrupción programada por registro; se excluyen datos personales no necesarios.',
        'actualizacion':'2026-05-11',
    },
    'socrata-acueductos-antioquia': {
        'nombre':'Acueductos Antioquia',
        'entidad':'Superintendencia de Servicios Públicos Domiciliarios',
        'url':'https://www.datos.gov.co/d/vhwk-6xqe',
        'licencia':'CC BY-SA 4.0',
        'granularidad':'Prestador y municipio de prestación; catálogo de referencia.',
        'actualizacion':'2021-07-26',
    },
}


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def digest(values):
    raw=json.dumps(values,ensure_ascii=False,separators=(',',':'),sort_keys=True,default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def date_dmy(value):
    return datetime.strptime(value.strip(),'%d/%m/%Y').date().isoformat()


def number(value,allow_blank=False):
    value=str(value or '').strip().replace(',','.')
    if not value and allow_blank:return None
    n=Decimal(value)
    if not n.is_finite() or n<0:raise ValueError('número inválido')
    return n


def consumption_number(value,allow_blank=False):
    raw=str(value or '').strip()
    if not raw and allow_blank:return None
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+',raw):raw=raw.replace('.','')
    return number(raw,allow_blank)


def integer(value):
    raw=str(value or '').strip()
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+',raw):raw=raw.replace('.','')
    n=number(raw)
    if n!=n.to_integral_value():raise ValueError('entero inválido')
    return int(n)


class Command(BaseCommand):
    help='Importa conjuntos oficiales sin crear usuarios, medidores ni lecturas individuales.'

    def add_arguments(self,parser):
        parser.add_argument('--directorio',required=True)
        parser.add_argument('--actor',default='ejecución local autorizada')

    def handle(self,*args,**options):
        root=Path(options['directorio']).resolve()
        required=['pequenos.csv','gran_prestador.csv','cobertura.csv','interrupciones.json','acueductos_antioquia.json']
        missing=[name for name in required if not (root/name).is_file()]
        if missing:raise CommandError('Faltan archivos: '+', '.join(missing))
        actor=options['actor'][:200]
        with transaction.atomic(), connection.cursor() as cur:
            for source_id,meta in SOURCES.items():
                cur.execute('''INSERT INTO fuente_oficial(id,nombre,entidad,url,licencia,granularidad,fecha_actualizacion,importado_en)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(id) DO UPDATE SET nombre=EXCLUDED.nombre,entidad=EXCLUDED.entidad,url=EXCLUDED.url,
                    licencia=EXCLUDED.licencia,granularidad=EXCLUDED.granularidad,
                    fecha_actualizacion=EXCLUDED.fecha_actualizacion,importado_en=EXCLUDED.importado_en''',
                    [source_id,meta['nombre'],meta['entidad'],meta['url'],meta['licencia'],meta['granularidad'],meta['actualizacion'],utcnow()])
        jobs=[
            ('medata-pequenos',lambda:self.import_consumption(root/'pequenos.csv','medata-pequenos',True,actor)),
            ('medata-gran-prestador',lambda:self.import_consumption(root/'gran_prestador.csv','medata-gran-prestador',False,actor)),
            ('medata-cobertura',lambda:self.import_coverage(root/'cobertura.csv',actor)),
            ('socrata-interrupciones',lambda:self.import_interruptions(root/'interrupciones.json',actor)),
            ('socrata-acueductos-antioquia',lambda:self.import_providers(root/'acueductos_antioquia.json',actor)),
        ]
        for source_id,job in jobs:
            result=job()
            self.stdout.write(self.style.SUCCESS(f"{source_id}: {result}"))

    def record(self,source_id,actor,started,read,valid,rejected,stored,detail):
        state='completada' if rejected==0 else 'con rechazos'
        with connection.cursor() as cur:
            cur.execute('''INSERT INTO importacion_datos_abiertos
                (fuente_id,iniciado_en,finalizado_en,actor,filas_leidas,filas_validas,filas_rechazadas,registros_almacenados,estado,detalle)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                [source_id,started,utcnow(),actor,read,valid,rejected,stored,state,detail])

    def import_consumption(self,path,source_id,has_total,actor):
        started=utcnow(); read=valid=rejected=excluded=0; rows=[]; reject_samples=[]
        with path.open(newline='',encoding='utf-8-sig') as stream:
            for item in csv.DictReader(stream):
                read+=1
                if item.get('servicio','').strip().lower()!='acueducto':excluded+=1;continue
                try:
                    row={
                        'prestador':item['prestador'].strip(),
                        'municipio':item.get('nombre','Medellín').strip() or 'Medellín',
                        'servicio':'Acueducto','periodo':date_dmy(item['periodo']),
                        'estrato':item['estrato'].strip(),'suscriptores':integer(item['suscriptores']),
                        'basico':consumption_number(item['consumo_basico_m3'],True),
                        'complementario':consumption_number(item.get('consumo_complementario_y_suntuario_m3'),True),
                        'total':consumption_number(item.get('total_consumo'),True) if has_total else None,
                    }
                    row['calidad_alerta']=None
                    if has_total and row['basico'] is not None and row['complementario'] is not None and row['total']!=row['basico']+row['complementario']:
                        row['calidad_alerta']='El total publicado no coincide con básico + complementario; se conserva el valor original.'
                    row['huella']=digest(row);rows.append(row);valid+=1
                except (KeyError,ValueError,InvalidOperation) as exc:
                    rejected+=1
                    if len(reject_samples)<5:reject_samples.append(f"fila {read+1}: {type(exc).__name__}: {exc}")
        sql='''INSERT INTO consumo_reportado(fuente_id,huella,prestador,municipio,servicio,periodo,estrato_uso,suscriptores,consumo_basico_m3,consumo_complementario_m3,consumo_total_m3,calidad_alerta)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(fuente_id,prestador,municipio,servicio,periodo,estrato_uso) DO UPDATE SET huella=EXCLUDED.huella,suscriptores=EXCLUDED.suscriptores,
            consumo_basico_m3=EXCLUDED.consumo_basico_m3,consumo_complementario_m3=EXCLUDED.consumo_complementario_m3,consumo_total_m3=EXCLUDED.consumo_total_m3,calidad_alerta=EXCLUDED.calidad_alerta'''
        with transaction.atomic(),connection.cursor() as cur:
            cur.executemany(sql,[[source_id,r['huella'],r['prestador'],r['municipio'],r['servicio'],r['periodo'],r['estrato'],r['suscriptores'],r['basico'],r['complementario'],r['total'],r['calidad_alerta']] for r in rows])
            cur.execute('SELECT COUNT(*) FROM consumo_reportado WHERE fuente_id=%s',[source_id]);stored=cur.fetchone()[0]
            detail=f'{excluded} filas de alcantarillado excluidas por alcance; granularidad agregada preservada.'
            if reject_samples:detail+=' Rechazos: '+' | '.join(reject_samples)
            self.record(source_id,actor,started,read,valid,rejected,stored,detail)
        return f'{stored} registros almacenados; {excluded} excluidos; {rejected} rechazados'

    def import_coverage(self,path,actor):
        source_id='medata-cobertura';started=utcnow();read=valid=rejected=excluded=0;rows=[]
        with path.open(newline='',encoding='utf-8-sig') as stream:
            for item in csv.DictReader(stream):
                read+=1
                if item.get('servicio','').strip().lower()!='acueducto':excluded+=1;continue
                try:
                    row={'municipio':'Medellín','comuna':item['comuna'].strip(),'servicio':'Acueducto','periodo':date_dmy(item['periodo']),
                         'estrato':item['estrato'].strip(),'suscriptores':integer(item['suscriptores']),
                         'cobertura':number(item['cobertura'].strip().rstrip('%'))}
                    row['calidad_alerta']='Valor publicado superior a 100 %; se conserva para revisión de calidad.' if row['cobertura']>100 else None
                    row['huella']=digest(row);rows.append(row);valid+=1
                except (KeyError,ValueError,InvalidOperation):rejected+=1
        sql='''INSERT INTO cobertura_reportada(fuente_id,huella,municipio,comuna,servicio,periodo,estrato_uso,suscriptores,cobertura_pct,calidad_alerta)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(fuente_id,municipio,comuna,servicio,periodo,estrato_uso) DO UPDATE SET huella=EXCLUDED.huella,suscriptores=EXCLUDED.suscriptores,cobertura_pct=EXCLUDED.cobertura_pct,calidad_alerta=EXCLUDED.calidad_alerta'''
        with transaction.atomic(),connection.cursor() as cur:
            cur.executemany(sql,[[source_id,r['huella'],r['municipio'],r['comuna'],r['servicio'],r['periodo'],r['estrato'],r['suscriptores'],r['cobertura'],r['calidad_alerta']] for r in rows])
            cur.execute('SELECT COUNT(*) FROM cobertura_reportada WHERE fuente_id=%s',[source_id]);stored=cur.fetchone()[0]
            self.record(source_id,actor,started,read,valid,rejected,stored,f'{excluded} filas de alcantarillado o aseo excluidas por alcance.')
        return f'{stored} registros almacenados; {excluded} excluidos; {rejected} rechazados'

    def import_interruptions(self,path,actor):
        source_id='socrata-interrupciones';started=utcnow();data=json.loads(path.read_text(encoding='utf-8'));read=len(data);rejected=0;unique={}
        for item in data:
            try:
                row={'prestador':'Empresas Públicas de Medellín','municipio':item['municipio'].strip(),
                     'inicio':item['inicio'][:19],'fin':item.get('fin','')[:19] or None,
                     'horas':number(item.get('horas'),True),'motivo':item.get('motivo','').strip() or None,
                     'impacto':item.get('impacto','').strip() or None,'circuito':item.get('circuito','').strip() or None,
                     'barrio':item.get('barrio','').strip() or None,'direccion':item.get('direccion','').strip() or None,
                     'estado':item.get('estado','').strip() or None}
                datetime.fromisoformat(row['inicio']);
                if row['fin']:datetime.fromisoformat(row['fin'])
                row['huella']=digest(row);unique[row['huella']]=row
            except (KeyError,ValueError,InvalidOperation):rejected+=1
        rows=list(unique.values());sql='''INSERT INTO interrupcion_oficial(fuente_id,huella,prestador,municipio,inicio,fin,duracion_horas,motivo,impacto,circuito,barrio,direccion,estado)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(fuente_id,huella) DO UPDATE SET fin=EXCLUDED.fin,duracion_horas=EXCLUDED.duracion_horas,estado=EXCLUDED.estado'''
        with transaction.atomic(),connection.cursor() as cur:
            cur.executemany(sql,[[source_id,r['huella'],r['prestador'],r['municipio'],r['inicio'],r['fin'],r['horas'],r['motivo'],r['impacto'],r['circuito'],r['barrio'],r['direccion'],r['estado']] for r in rows])
            cur.execute('SELECT COUNT(*) FROM interrupcion_oficial WHERE fuente_id=%s',[source_id]);stored=cur.fetchone()[0]
            self.record(source_id,actor,started,read,len(rows),rejected,stored,f'{read-len(rows)-rejected} duplicados exactos consolidados. Se omitieron responsables, teléfonos y explicaciones con contactos.')
        return f'{stored} registros únicos almacenados; {rejected} rechazados'

    def import_providers(self,path,actor):
        source_id='socrata-acueductos-antioquia';started=utcnow();data=json.loads(path.read_text(encoding='utf-8'));read=len(data);rejected=0;rows=[]
        for item in data:
            try:
                row={'nombre':item['nombre'].strip(),'servicio':item['servicio'].strip(),
                     'municipio_prestacion':item['municipio_prestacion'].strip(),'municipio_domicilio':item.get('municipio_domicilio','').strip() or None}
                if not all([row['nombre'],row['servicio'],row['municipio_prestacion']]):raise ValueError()
                row['huella']=digest(row);rows.append(row)
            except (KeyError,ValueError):rejected+=1
        sql='''INSERT INTO prestador_oficial(fuente_id,huella,nombre,servicio,municipio_prestacion,municipio_domicilio)
            VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(fuente_id,huella) DO UPDATE SET nombre=EXCLUDED.nombre'''
        with transaction.atomic(),connection.cursor() as cur:
            cur.executemany(sql,[[source_id,r['huella'],r['nombre'],r['servicio'],r['municipio_prestacion'],r['municipio_domicilio']] for r in rows])
            cur.execute('SELECT COUNT(*) FROM prestador_oficial WHERE fuente_id=%s',[source_id]);stored=cur.fetchone()[0]
            self.record(source_id,actor,started,read,len(rows),rejected,stored,'Se importaron solo nombre, servicio y municipios; se excluyeron contactos y representante legal.')
        return f'{stored} registros almacenados; {rejected} rechazados'
