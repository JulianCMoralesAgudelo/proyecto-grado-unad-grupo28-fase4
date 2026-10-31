# Proyecto de Grado 202016907 — Grupo 28 — Fase 4

Prototipo académico de gestión de usuarios, predios, medidores, lecturas, consumos y novedades de acueductos rurales. Los datos y organizaciones de demostración son ficticios.

## Ejecutar localmente

Requisitos: Docker y Docker Compose. Desde esta carpeta:

1. `python preparar.py` crea credenciales locales que no deben publicarse.
2. `docker compose up -d --build` inicia PostgreSQL y Django.
3. Abrir `http://127.0.0.1:8086` y consultar `credenciales_locales.txt` en el equipo local.
4. `python comprobar_docker.py` registra la comprobación Django y las pruebas integradas.

`python verificar.py` ejecuta aparte una campaña WSGI/SQLite. Sus resultados no sustituyen las pruebas Django/PostgreSQL ni la validación con personas.

## Alcance de la entrega

El repositorio contiene únicamente el código, configuración de ejemplo, migraciones y pruebas del prototipo. El documento maestro, el video y la valoración TRL se entregan mediante los enlaces indicados en el documento académico. No se incluyen contraseñas, bases de datos ni respaldos.
