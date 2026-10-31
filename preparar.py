"""Crea credenciales locales nuevas sin incluirlas en el código fuente."""
from pathlib import Path
import secrets
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    target=ROOT/'.env'
    if target.exists():print('Configuración existente conservada; no se sobrescribe.')
    else:
        password=secrets.token_urlsafe(20)
        target.write_text('POSTGRES_PASSWORD='+secrets.token_urlsafe(32)+'\nSECRET_KEY='+secrets.token_urlsafe(48)+'\nDEMO_PASSWORD='+password+'\n',encoding='utf-8')
        (ROOT/'credenciales_locales.txt').write_text('SOLO ENTORNO SINTETICO LOCAL. No subir este archivo ni .env a GitHub.\nCuentas: sim-a-admin, sim-a-operador, sim-a-consulta; y equivalentes sim-b.\nClave de las seis cuentas: '+password+'\nCambiar de cuenta requiere cerrar sesión. Datos ficticios.\n',encoding='utf-8')
        print('Configuración creada. Consulta credenciales_locales.txt para ingresar. No publicar credenciales.')
