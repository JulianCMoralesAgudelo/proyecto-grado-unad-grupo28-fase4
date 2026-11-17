from django.db import migrations

FORWARD="""
ALTER TABLE consumo_reportado ADD COLUMN IF NOT EXISTS calidad_alerta TEXT;
ALTER TABLE cobertura_reportada ADD COLUMN IF NOT EXISTS calidad_alerta TEXT;
ALTER TABLE cobertura_reportada DROP CONSTRAINT IF EXISTS cobertura_reportada_cobertura_pct_check;
ALTER TABLE cobertura_reportada ADD CONSTRAINT cobertura_reportada_cobertura_pct_check CHECK(cobertura_pct >= 0);
"""
REVERSE="""
ALTER TABLE cobertura_reportada DROP COLUMN IF EXISTS calidad_alerta;
ALTER TABLE consumo_reportado DROP COLUMN IF EXISTS calidad_alerta;
"""

class Migration(migrations.Migration):
    dependencies=[('operacion','0002_datos_abiertos')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
