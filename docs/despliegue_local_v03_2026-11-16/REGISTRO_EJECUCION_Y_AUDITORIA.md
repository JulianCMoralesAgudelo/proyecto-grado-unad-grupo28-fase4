# Registro de ejecución y auditoría del despliegue local v0.3

Fecha local: 16 de noviembre de 2026. Fecha UTC del ensayo: 17 de noviembre de 2026. Alcance: Fedora local, Docker Compose y datos completamente sintéticos.

## Fuentes cotejadas

- Instrucciones generales del repositorio y `Proyecto_de_Grado_202016907A_2204/AGENTS.md`.
- Guía y rúbrica oficiales de Fase 4.
- Anexos E, H y K del Documento Maestro v15, conservado sin modificaciones.
- Código del prototipo en el commit académico `cdb3349993ee184e4c6e3a53d7e3711bcb584e6f`.
- Repositorio público `https://github.com/JulianCMoralesAgudelo/proyecto-grado-unad-grupo28-fase4`, rama `main`, commit `d43bc5acb3afec4e1689e803a3582b4dfc943e81`.

## Correspondencia de versión

El árbol académico del prototipo es `7e0da2f5ff4b5dc12e07cef737a61afe3074c161`. La comparación de nombres y blobs confirmó que los 32 archivos del prototipo académico coinciden con el commit público `d43bc5a`; el repositorio público contiene además `README.md`. La versión observada por la API fue `0.3.0-simulacion`.

## Laboratorio desplegado

- Carpeta de ejecución: `Proyectos/G4/tmp/despliegue_local_manual_v03/`.
- Proyecto Compose: `pdg28-manual-v03`.
- URL: `http://127.0.0.1:18087`.
- Servicio web: publicado solo en `127.0.0.1:18087`.
- PostgreSQL: accesible únicamente en la red de Compose; no publica puerto al host.
- Persistencia: volumen `pdg28-manual-v03_pgdata`.
- Fedora 44, kernel 7.3.3-200.fc44.x86_64, Docker Engine 29.10.0, Docker Compose 5.7.1, Django 5.2.19 y PostgreSQL 16.15.

## Comandos ejecutados

```bash
git archive cdb33499:Proyecto_de_Grado_202016907A_2204/Proyectos/G4/prototipo_fase4 | tar -x -C Proyecto_de_Grado_202016907A_2204/Proyectos/G4/tmp/despliegue_local_manual_v03
cd Proyecto_de_Grado_202016907A_2204/Proyectos/G4/tmp/despliegue_local_manual_v03
python3 iniciar.py
docker compose ps
python3 comprobar_docker.py
docker compose exec -T db postgres --version
docker compose exec -T web python -m django --version
```

La copia de laboratorio cambió únicamente el nombre del proyecto Compose y el puerto local de `127.0.0.1:8086` a `127.0.0.1:18087`, porque el puerto 18086 estaba ocupado por el ensayo CP16a/CP17a. No se modificó la fuente versionada.

## Resultado del arranque

Las migraciones se aplicaron y la siembra creó dos organizaciones ficticias, seis cuentas, 16 usuarios y 48 lecturas. `comprobar_docker.py` aprobó la verificación de versiones, `manage.py check` y las 16 pruebas Django/PostgreSQL. Al cierre, `db` estaba saludable y `web` activo.

## Verificación técnica de roles y tareas

El ensayo técnico inició sesión localmente como administrador, operador y consulta de SIM-A y como consulta de SIM-B, sin registrar contraseñas. Se observaron los permisos esperados: administración y exportación para `sim-a-admin`, escritura operativa sin administración para `sim-a-operador`, y lectura sin escritura ni exportación para `sim-a-consulta`. Un intento de escritura del rol consulta devolvió HTTP 403 con el mensaje `Permiso denegado`. SIM-B mostró únicamente seriales de su organización.

| Tarea | Datos técnicos preparados | Resultado por API | Estado en Edge |
| --- | --- | --- | --- |
| M01a | U001, marzo de 2026; lecturas 100,000 y 112,250 m³ | Histórico y consumo de 12,250 m³ coherentes | Pendiente de recorrido manual |
| M01b | Instalación 1; 1 de mayo de 2026; lectura 136,750 m³ | Lectura válida persistida y consumo de 12,250 m³ | Pendiente de recorrido manual |
| M01c | Novedad sintética 1; corte posterior a su apertura | Estado `abierta` coherente | Pendiente de recorrido manual |

## Limitación de Microsoft Edge

El usuario abrió Microsoft Edge, pero la herramienta autorizada de control devolvió de forma repetida `browser access host is unavailable`, tanto al inventariar navegadores como al intentar enlazar Edge. No se utilizó otro navegador. Por esta razón no se observaron en Edge los formularios, mensajes ni resultados, no se generaron capturas nuevas y no se emite dictamen de interfaz para M01a-c.

Esta limitación no equivale a un fallo del prototipo: la URL respondió, la API y los roles funcionaron, y la suite Django/PostgreSQL aprobó. Los tres casos quedan preparados para repetición manual en Edge con los datos indicados en los manuales.

## Alcance de CP18a

Esta ejecución es un ensayo interno técnico. No constituye CP18a. El dictamen de CP18a solo puede calcularse con los primeros intentos elegibles de participantes autorizados, después de una explicación uniforme y una práctica fuera de medición. El éxito exige resultado correcto en hasta 300 segundos y sin ayuda; ayudas, fallos y abandonos iniciados permanecen en el denominador. Sin esos intentos no se calcula porcentaje ni se emite dictamen.

## Comandos de operación

Desde la carpeta del laboratorio:

```bash
# Estado
docker compose ps

# Logs recientes y seguimiento
docker compose logs --tail=100 web db
docker compose logs -f web db

# Detener conservando el volumen PostgreSQL
docker compose stop

# Volver a iniciar
docker compose start
```

No ejecutar `docker compose down -v`, porque elimina el volumen persistente del laboratorio.

## Seguridad y exclusiones

Los archivos `.env` y `credenciales_locales.txt` permanecen únicamente en la carpeta de ejecución y están excluidos del entregable. No se copiaron contraseñas, tokens, cookies ni secretos. La búsqueda en la carpeta de evidencias no encontró esos valores. Los documentos indican dónde consultar las cuentas localmente, sin reproducir la clave.

## Evidencias conservadas

- `evidencias/versiones.txt`.
- `evidencias/correspondencia_commits.txt`.
- `evidencias/docker_compose_ps.txt`.
- `evidencias/docker_compose_logs.txt`.
- `evidencias/verificacion_servicios_frontend.json`.

## Hallazgos, correcciones y pendientes

- Hallazgo: el puerto 18086 estaba ocupado. Corrección: se asignó 18087 manteniendo la publicación en loopback.
- Hallazgo: Edge externo no pudo ser controlado. Acción: se conservó el error exacto, no se sustituyó el navegador y se prepararon casos manuales.
- Pendientes: ejecutar M01a-c manualmente en Edge, incorporar capturas sin datos de acceso si se requieren y aplicar CP18a con participantes autorizados.
- El Documento Maestro v15 no fue modificado.

## Auditoría de entregables

Auditoría cerrada el 16 de noviembre de 2026 sobre la versión exacta compartida. Los dos manuales se cotejaron con la guía, la rúbrica, los anexos E, H y K, el código v0.3 y este registro.

- Se verificaron portada institucional, papel carta, márgenes de 2,54 cm, Times New Roman de 12 puntos en el cuerpo, texto justificado, títulos y tablas centrados, paginación superior derecha e índices con páginas concordantes.
- Se renderizaron e inspeccionaron visualmente todas las páginas: 5 en el manual de uso y 7 en el manual de pruebas. No se observaron textos cortados, superposiciones, tablas ilegibles ni saltos defectuosos.
- Los PDF se generaron desde los Word finales y conservan el mismo contenido, tamaño carta, paginación y enlaces. El vínculo al repositorio público se comprobó en ambos Word.
- La primera exportación dejó vacío el índice automático; se corrigió con índices estáticos verificados y se volvió a renderizar.
- La búsqueda final no encontró secretos en los entregables. Las menciones a `.env`, contraseñas o tokens son únicamente advertencias de exclusión; no contienen valores.
- El Documento Maestro v15 permaneció intacto. SHA-256: `36b2b9b62800141480f267ea19777152b5cb686499d3ba92b5b50081c1efde87`.

Huellas SHA-256 de cierre:

- Manual de uso DOCX: `1c1ceb0c780fe4192bd7f995d95f393e2d51fc3b93f378627da4291f880cabe7`.
- Manual de uso PDF: `b229520637c81dfd0420c4f01cd06a147d3ff902473cb8c9f28e5e65373ee571`.
- Manual de pruebas DOCX: `26c9e45aa50c9ff717f0ce99f1be84ad189a87c0660e08043f2f85fc48f290e6`.
- Manual de pruebas PDF: `e2b534f0f00eaffa856911f64792cc969aaba0334a327f9b3e06491bcb445dc7`.

Estado de cierre: entregables documentales terminados; servicios web y base de datos activos. Pendiente explícito: ejecución manual de M01a-c en Microsoft Edge externo y, posteriormente, CP18a con participantes autorizados.
