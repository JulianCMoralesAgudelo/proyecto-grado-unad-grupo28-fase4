# Agua Antioquia · Proyecto de Grado · Grupo 28

Prototipo académico de la Fase 4 para gestionar usuarios, predios, medidores, lecturas, consumos y novedades de acueductos rurales. El escenario de demostración usa datos ficticios.

## Versión 0.3

Los 31 archivos del prototipo corresponden al árbol `7e0da2f5ff4b5dc12e07cef737a61afe3074c161` del commit académico `cdb3349993ee184e4c6e3a53d7e3711bcb584e6f`. Este README documenta el arranque y la verificación.

## Ejecutar en local

Con Python 3, Docker y Docker Compose, ejecutar `python3 iniciar.py` en esta carpeta. El script prepara la configuración local, aplica las migraciones e inicializa el escenario de demostración. Abrir `http://127.0.0.1:8086` y consultar las cuentas de demostración en `credenciales_locales.txt` en el equipo local.

Ejecutar `python3 comprobar_docker.py` para conservar los registros de Django y las pruebas de integración. Consultar `LEEME.txt` para el recorrido de demostración.

## Evidencia de integración

El 16 de noviembre de 2026 se ejecutó esta revisión en Fedora 44 con Docker Engine 29.10.0. Django 5.2.19 superó `manage.py check` y se aprobaron 16 de 16 pruebas de integración con PostgreSQL en 13,343 segundos. La validación en condiciones representativas, la aceptación con participantes y la valoración de TRL 5 se documentan en el proyecto académico.

Los archivos `.env`, las credenciales locales y las bases de datos se generan en el equipo de prueba.
