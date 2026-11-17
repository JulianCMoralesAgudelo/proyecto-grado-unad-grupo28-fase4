from pathlib import Path
from django.db import migrations

SQL=(Path(__file__).resolve().parents[2]/"schema_datos_abiertos_postgresql.sql").read_text(encoding="utf-8")
REVERSE="""
DROP TABLE IF EXISTS importacion_datos_abiertos;
DROP TABLE IF EXISTS prestador_oficial;
DROP TABLE IF EXISTS interrupcion_oficial;
DROP TABLE IF EXISTS cobertura_reportada;
DROP TABLE IF EXISTS consumo_reportado;
DROP TABLE IF EXISTS fuente_oficial;
"""

class Migration(migrations.Migration):
    dependencies=[('operacion','0001_initial')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
