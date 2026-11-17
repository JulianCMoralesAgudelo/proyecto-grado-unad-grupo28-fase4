# Inventario de datos abiertos integrados

Fecha de validación e importación local: 17 de noviembre de 2026.

La aplicación conserva la granularidad publicada. Ningún total de suscriptores se transforma en usuarios individuales y ningún consumo agregado se transforma en lectura de medidor. Las tablas de práctica SIM-A y SIM-B permanecen separadas.

| Dataset | Fuente oficial | Período | Registros de acueducto almacenados | Estado | Módulo |
| --- | --- | --- | ---: | --- | --- |
| Suscriptores y consumos de pequeños prestadores | MEData, Alcaldía de Medellín | 2017-12-31 a 2023-09-30 | 15.350 | Integrado | Consumos reportados |
| Suscriptores y consumos del gran prestador | MEData, Alcaldía de Medellín | 2017-12-31 a 2023-08-31 | 690 | Integrado | Consumos reportados |
| Micromedición | SUI, Superservicios | Desde 2002 según la ficha | 0 | Pendiente: el visor oficial requiere consulta y exportación interactiva; no se simuló descarga | No habilitado |
| Consolidado comercial | SUI, Superservicios | No verificado en archivo descargable | 0 | Pendiente: no se obtuvo archivo reproducible en esta ejecución | No habilitado |
| Distribución de agua potable | SUI, Superservicios | No verificado en archivo descargable | 0 | Pendiente: no se obtuvo archivo reproducible en esta ejecución | No habilitado |
| Agua producida y macromedición | SUI, Superservicios | No verificado en archivo descargable | 0 | Pendiente: no se obtuvo archivo reproducible en esta ejecución | No habilitado |
| Interrupciones programadas del servicio de acueducto | E.S.P. Empresas Públicas de Medellín - EPM, Datos Abiertos Colombia, `r9fv-awbc`, CC BY-SA 4.0 | 2022-11-15 a 2026-05-18 en la descarga | 1.693 registros únicos | Integrado; contactos personales excluidos | Interrupciones oficiales |
| Reporte de estratificación y cobertura | MEData, Alcaldía de Medellín | 2017-12-31 a 2019-12-31 | 317 | Integrado | Cobertura reportada |
| Acueductos Antioquia | Superservicios, Datos Abiertos Colombia, `vhwk-6xqe`, CC BY-SA 4.0 | Sin período en los registros descargados | 494 registros únicos | Integrado; contactos y representante legal excluidos | Directorio de prestadores |

## Transformaciones verificables

- Se conservaron los nombres de prestador, período, estrato o uso, suscriptores y consumos publicados.
- Se filtró `Acueducto`; las filas de alcantarillado y aseo no se importaron en estas entidades.
- Las fechas `dd/mm/aaaa` se normalizaron a ISO `aaaa-mm-dd`.
- Los puntos usados como separador de miles en campos numéricos del CSV se retiraron solo cuando seguían el patrón de grupos de tres dígitos.
- Las 232 filas de pequeños prestadores cuyo total publicado no coincide con básico más complementario se conservaron con alerta de calidad.
- Los 31 porcentajes de cobertura superiores a 100 se conservaron con alerta de calidad; no se corrigieron ni limitaron.
- De interrupciones se excluyeron responsables, teléfonos, contratistas y explicaciones que contienen contactos. Se conservaron municipio, fechas, duración, motivo, impacto, circuito, barrio, dirección y estado.
- Del directorio se conservaron nombre, servicio y municipios. Se excluyeron correo, teléfono, dirección y representante legal.
- Las huellas SHA-256 y claves naturales impiden duplicados al repetir la importación.

## Ejecución reproducible

```bash
python manage.py migrate --noinput
python manage.py importar_datos_abiertos --directorio /app/datos_abiertos/originales --actor "responsable de la importación"
```

Los archivos originales y sus diccionarios están en `datos_abiertos/originales/`. La tabla `importacion_datos_abiertos` conserva fecha, actor, filas leídas, válidas, rechazadas, almacenadas y detalle de cada ejecución.
