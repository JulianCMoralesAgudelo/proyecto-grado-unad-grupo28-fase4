CREATE TABLE IF NOT EXISTS fuente_oficial(
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    entidad TEXT NOT NULL,
    url TEXT NOT NULL,
    licencia TEXT,
    granularidad TEXT NOT NULL,
    fecha_actualizacion TEXT,
    importado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consumo_reportado(
    id BIGSERIAL PRIMARY KEY,
    fuente_id TEXT NOT NULL REFERENCES fuente_oficial(id),
    huella TEXT NOT NULL,
    prestador TEXT NOT NULL,
    municipio TEXT,
    servicio TEXT NOT NULL,
    periodo DATE NOT NULL,
    estrato_uso TEXT NOT NULL,
    suscriptores BIGINT NOT NULL CHECK(suscriptores >= 0),
    consumo_basico_m3 NUMERIC(20,3),
    consumo_complementario_m3 NUMERIC(20,3),
    consumo_total_m3 NUMERIC(20,3),
    calidad_alerta TEXT,
    UNIQUE(fuente_id,huella)
);

CREATE TABLE IF NOT EXISTS cobertura_reportada(
    id BIGSERIAL PRIMARY KEY,
    fuente_id TEXT NOT NULL REFERENCES fuente_oficial(id),
    huella TEXT NOT NULL,
    municipio TEXT NOT NULL,
    comuna TEXT NOT NULL,
    servicio TEXT NOT NULL,
    periodo DATE NOT NULL,
    estrato_uso TEXT NOT NULL,
    suscriptores BIGINT NOT NULL CHECK(suscriptores >= 0),
    cobertura_pct NUMERIC(7,3) NOT NULL CHECK(cobertura_pct >= 0),
    calidad_alerta TEXT,
    UNIQUE(fuente_id,huella)
);

CREATE TABLE IF NOT EXISTS interrupcion_oficial(
    id BIGSERIAL PRIMARY KEY,
    fuente_id TEXT NOT NULL REFERENCES fuente_oficial(id),
    huella TEXT NOT NULL,
    prestador TEXT NOT NULL,
    municipio TEXT NOT NULL,
    inicio TIMESTAMP NOT NULL,
    fin TIMESTAMP,
    duracion_horas NUMERIC(12,3),
    motivo TEXT,
    impacto TEXT,
    circuito TEXT,
    barrio TEXT,
    direccion TEXT,
    estado TEXT,
    UNIQUE(fuente_id,huella)
);

CREATE TABLE IF NOT EXISTS prestador_oficial(
    id BIGSERIAL PRIMARY KEY,
    fuente_id TEXT NOT NULL REFERENCES fuente_oficial(id),
    huella TEXT NOT NULL,
    nombre TEXT NOT NULL,
    servicio TEXT NOT NULL,
    municipio_prestacion TEXT NOT NULL,
    municipio_domicilio TEXT,
    UNIQUE(fuente_id,huella)
);

CREATE TABLE IF NOT EXISTS importacion_datos_abiertos(
    id BIGSERIAL PRIMARY KEY,
    fuente_id TEXT NOT NULL REFERENCES fuente_oficial(id),
    iniciado_en TEXT NOT NULL,
    finalizado_en TEXT NOT NULL,
    actor TEXT NOT NULL,
    filas_leidas BIGINT NOT NULL,
    filas_validas BIGINT NOT NULL,
    filas_rechazadas BIGINT NOT NULL,
    registros_almacenados BIGINT NOT NULL,
    estado TEXT NOT NULL CHECK(estado IN('completada','con rechazos','fallida')),
    detalle TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS consumo_reportado_filtros ON consumo_reportado(fuente_id,periodo,prestador,municipio);
CREATE INDEX IF NOT EXISTS cobertura_reportada_filtros ON cobertura_reportada(periodo,municipio,comuna);
CREATE INDEX IF NOT EXISTS interrupcion_oficial_filtros ON interrupcion_oficial(inicio,municipio,motivo);
CREATE INDEX IF NOT EXISTS prestador_oficial_filtros ON prestador_oficial(municipio_prestacion,nombre);
