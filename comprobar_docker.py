"""Conserva resultados reales del entorno objetivo sin inventar aprobaciones."""
from pathlib import Path
import subprocess
import datetime
import json
ROOT=Path(__file__).resolve().parent
EVID=ROOT.parent/'evidencias_fase4'

if __name__=='__main__':
    EVID.mkdir(exist_ok=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    jobs=[('versiones',['docker','compose','exec','-T','web','python','-m','pip','freeze']),('django_check',['docker','compose','run','--rm','web','python','manage.py','check']),('django_postgresql_tests',['docker','compose','run','--rm','web','python','manage.py','test','operacion','--noinput','--verbosity','2'])]
    results=[]
    for name,cmd in jobs:
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        logfile=EVID/f'{stamp}_{name}.txt'
        logfile.write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
        results.append({'prueba':name,'fecha_utc':stamp,'estado':'aprobado' if r.returncode==0 else 'fallido','codigo_salida':r.returncode,'evidencia':logfile.name})
        print(name,results[-1]['estado'])
    (EVID/f'{stamp}_resumen_docker.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if all(x['estado']=='aprobado' for x in results) else 1)
