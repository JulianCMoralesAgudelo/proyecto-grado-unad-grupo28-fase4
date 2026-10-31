
CREATE TABLE IF NOT EXISTS acueducto(id TEXT PRIMARY KEY,nombre TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cuenta(id BIGSERIAL PRIMARY KEY,aq TEXT NOT NULL REFERENCES acueducto(id),login TEXT UNIQUE NOT NULL,hash TEXT NOT NULL,rol TEXT NOT NULL CHECK(rol IN('admin','operador','consulta')),exportar BIGINT NOT NULL DEFAULT 0 CHECK(exportar IN(0,1)),activo BIGINT NOT NULL DEFAULT 1,UNIQUE(aq,id));
CREATE TABLE IF NOT EXISTS sesion(token TEXT PRIMARY KEY,cuenta BIGINT NOT NULL REFERENCES cuenta(id),csrf TEXT NOT NULL,expira REAL NOT NULL);
CREATE TABLE IF NOT EXISTS usuario(id BIGSERIAL PRIMARY KEY,aq TEXT NOT NULL REFERENCES acueducto(id),codigo TEXT NOT NULL,activo BIGINT NOT NULL DEFAULT 1,UNIQUE(aq,codigo),UNIQUE(aq,id));
CREATE TABLE IF NOT EXISTS predio(id BIGSERIAL PRIMARY KEY,aq TEXT NOT NULL,codigo TEXT NOT NULL,usuario BIGINT NOT NULL,FOREIGN KEY(aq,usuario) REFERENCES usuario(aq,id),UNIQUE(aq,codigo),UNIQUE(aq,id));
CREATE TABLE IF NOT EXISTS medidor(id BIGSERIAL PRIMARY KEY,aq TEXT NOT NULL REFERENCES acueducto(id),serial TEXT NOT NULL,UNIQUE(aq,serial),UNIQUE(aq,id));
CREATE TABLE IF NOT EXISTS instalacion(id BIGSERIAL PRIMARY KEY,aq TEXT NOT NULL,predio BIGINT NOT NULL,medidor BIGINT NOT NULL,inicio TEXT NOT NULL,fin TEXT,CHECK(fin IS NULL OR fin>inicio),FOREIGN KEY(aq,predio) REFERENCES predio(aq,id),FOREIGN KEY(aq,medidor) REFERENCES medidor(aq,id),UNIQUE(aq,id));
CREATE TABLE IF NOT EXISTS lectura(id BIGSERIAL PRIMARY KEY,aq TEXT NOT NULL,instalacion BIGINT NOT NULL,fecha TEXT NOT NULL,valor BIGINT NOT NULL CHECK(valor>=0),estado TEXT NOT NULL CHECK(estado IN('valida','pendiente','descartada')),FOREIGN KEY(aq,instalacion) REFERENCES instalacion(aq,id),UNIQUE(instalacion,fecha),UNIQUE(aq,id));
CREATE TABLE IF NOT EXISTS novedad(id BIGSERIAL PRIMARY KEY,aq TEXT NOT NULL REFERENCES acueducto(id),descripcion TEXT NOT NULL,estado TEXT NOT NULL CHECK(estado IN('abierta','en gestion','cerrada')),apertura TEXT NOT NULL,cierre TEXT,motivo TEXT);
CREATE TABLE IF NOT EXISTS auditoria(id BIGSERIAL PRIMARY KEY,aq TEXT NOT NULL,actor BIGINT NOT NULL,instante TEXT NOT NULL,entidad TEXT NOT NULL,registro BIGINT NOT NULL,accion TEXT NOT NULL,anterior TEXT,posterior TEXT,motivo TEXT NOT NULL,FOREIGN KEY(aq,actor) REFERENCES cuenta(aq,id));
CREATE INDEX IF NOT EXISTS lectura_serie ON lectura(aq,instalacion,fecha);
CREATE INDEX IF NOT EXISTS auditoria_aq ON auditoria(aq,id);

CREATE FUNCTION proteger_auditoria() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Auditoria inmutable' USING ERRCODE='23514'; END; $$;
CREATE TRIGGER auditoria_no_update BEFORE UPDATE OR DELETE ON auditoria FOR EACH ROW EXECUTE FUNCTION proteger_auditoria();
