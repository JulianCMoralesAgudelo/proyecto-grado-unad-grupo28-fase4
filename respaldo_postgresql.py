"""Copia nueva sin sobrescribir y restauración opcional a base nueva."""
from pathlib import Path
import subprocess
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    dest=ROOT/'datos'/'respaldos';dest.mkdir(parents=True,exist_ok=True)
    target=dest/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.dump')
    with target.open('xb') as f:
        r=subprocess.run(['docker','compose','exec','-T','db','pg_dump','-U','agua','-d','agua_simulada','-Fc'],cwd=ROOT,stdout=f)
    if r.returncode:raise SystemExit('Falló la copia. No usar el archivo como evidencia de recuperación.')
    print('Copia nueva creada:',target)
    print('Pendiente restaurarla en una base separada y verificar integridad antes de aprobar recuperación.')
