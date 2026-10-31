"""Inicio reproducible de Django/PostgreSQL desde una terminal del usuario."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent

def run(args):
    result=subprocess.run(args,cwd=ROOT)
    if result.returncode:raise SystemExit(result.returncode)

if __name__=='__main__':
    run(['docker','info','--format','{{.ServerVersion}}'])
    run([sys.executable,'preparar.py'])
    run(['docker','compose','build','web'])
    run(['docker','compose','up','-d','db'])
    run(['docker','compose','run','--rm','web','python','manage.py','migrate','--noinput'])
    run(['docker','compose','run','--rm','web','python','manage.py','sembrar_demo'])
    run(['docker','compose','up','-d','web'])
    print('Prototipo: http://127.0.0.1:8086')
    print('Cuentas y clave: credenciales_locales.txt. No publicar ese archivo ni .env.')
    print('Ejecuta python comprobar_docker.py para generar la evidencia del motor objetivo.')
