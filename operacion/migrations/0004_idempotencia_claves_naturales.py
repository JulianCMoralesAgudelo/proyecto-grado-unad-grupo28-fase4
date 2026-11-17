from django.db import migrations

FORWARD="""
DELETE FROM consumo_reportado antiguo USING consumo_reportado reciente
WHERE antiguo.id < reciente.id
  AND antiguo.fuente_id=reciente.fuente_id
  AND antiguo.prestador=reciente.prestador
  AND COALESCE(antiguo.municipio,'')=COALESCE(reciente.municipio,'')
  AND antiguo.servicio=reciente.servicio
  AND antiguo.periodo=reciente.periodo
  AND antiguo.estrato_uso=reciente.estrato_uso;
ALTER TABLE consumo_reportado ADD CONSTRAINT consumo_reportado_clave_natural
UNIQUE(fuente_id,prestador,municipio,servicio,periodo,estrato_uso);

DELETE FROM cobertura_reportada antiguo USING cobertura_reportada reciente
WHERE antiguo.id < reciente.id
  AND antiguo.fuente_id=reciente.fuente_id
  AND antiguo.municipio=reciente.municipio
  AND antiguo.comuna=reciente.comuna
  AND antiguo.servicio=reciente.servicio
  AND antiguo.periodo=reciente.periodo
  AND antiguo.estrato_uso=reciente.estrato_uso;
ALTER TABLE cobertura_reportada ADD CONSTRAINT cobertura_reportada_clave_natural
UNIQUE(fuente_id,municipio,comuna,servicio,periodo,estrato_uso);
"""
REVERSE="""
ALTER TABLE cobertura_reportada DROP CONSTRAINT IF EXISTS cobertura_reportada_clave_natural;
ALTER TABLE consumo_reportado DROP CONSTRAINT IF EXISTS consumo_reportado_clave_natural;
"""

class Migration(migrations.Migration):
    dependencies=[('operacion','0003_alertas_calidad')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
