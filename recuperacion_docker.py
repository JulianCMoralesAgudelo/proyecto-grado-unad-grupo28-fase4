"""Ensayo de restauración a una base NUEVA; conserva el origen y el destino."""
from pathlib import Path
import subprocess
import datetime
import time
import json
import uuid
ROOT=Path(__file__).resolve().parent
EVID=ROOT.parent/'evidencias_fase4'
TABLES=['usuario','predio','medidor','instalacion','lectura','novedad','auditoria']

def command(args,**kw):
    r=subprocess.run(['docker','compose','exec','-T','db']+args,cwd=ROOT,check=True,**kw)
    return r

def sql(db,q):return command(['psql','-U','agua','-d',db,'-At','-v','ON_ERROR_STOP=1','-c',q],capture_output=True,text=True).stdout.strip()

def snapshot(db):
    return {t:sql(db,f"SELECT COALESCE(json_agg(row_to_json(x))::text,'[]') FROM (SELECT * FROM {t} ORDER BY id) x") for t in TABLES}

if __name__=='__main__':
    EVID.mkdir(exist_ok=True)
    uid=uuid.uuid4().hex; target='ensayo_recuperacion_'+uid
    assert target.startswith('ensayo_recuperacion_') and target.replace('_','').isalnum()
    location=ROOT/'datos'/'respaldos';location.mkdir(parents=True,exist_ok=True)
    dump=location/(uid+'.dump')
    # Marking time before pg_dump gives a conservative temporal upper bound.
    marker=time.time();before=snapshot('agua_simulada')
    with dump.open('xb') as f:command(['pg_dump','-U','agua','-d','agua_simulada','-Fc','--no-owner','--no-privileges'],stdout=f)
    incident=time.time();start=time.perf_counter()
    command(['createdb','-U','agua',target])
    with dump.open('rb') as f:command(['pg_restore','-U','agua','-d',target,'--no-owner','--no-privileges','--exit-on-error'],stdin=f)
    # Remove copied sessions only in the newly created recovery database.
    sql(target,'DELETE FROM sesion')
    after=snapshot(target);rto=time.perf_counter()-start
    checks={t:before[t]==after[t] for t in TABLES}
    result={'fecha_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'motor':'PostgreSQL 16','destino_nuevo':target,'meta_RTO_s':60,'meta_RPO_s':120,'RTO_s':rto,'RPO_cota_superior_s':incident-marker,'comparacion_tablas':checks,'sesiones_destino':int(sql(target,'SELECT COUNT(*) FROM sesion')),'estado':'aprobado' if all(checks.values()) and rto<=60 and incident-marker<=120 else 'fallido','limites':'Restauración lógica aislada, sin destruir el origen; no es incidente real ni prueba de alta disponibilidad. La cota RPO se mide desde antes del respaldo; no desde la edad de un dato.'}
    path=EVID/(uid+'_recuperacion_postgresql.json');path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Resultado:',result['estado'],'- Evidencia:',path)
    print('La base nueva se conserva para inspección:',target)
    raise SystemExit(0 if result['estado']=='aprobado' else 1)
