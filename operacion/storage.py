"""Adaptador transaccional para los servicios compartidos.
PostgreSQL es el motor de la aplicación Django; SQLite solo para ensayo local.
"""
import sqlite3
from django.db import connection,transaction,IntegrityError

class Row(dict):
    def __getitem__(self,key):return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)

class Result:
    def __init__(self,rows,lastrowid=None):self.rows=rows;self.lastrowid=lastrowid
    def fetchone(self):return self.rows.pop(0) if self.rows else None
    def fetchall(self):rows=self.rows;self.rows=[];return rows
    def __iter__(self):return iter(self.rows)

class Database:
    def execute(self,sql,params=()):
        returns_id=sql.lstrip().upper().startswith('INSERT INTO ') and any(sql.lstrip().lower().startswith('insert into '+t+'(') or sql.lstrip().lower().startswith('insert into '+t+' ') for t in ['usuario','predio','medidor','instalacion','lectura','novedad'])
        statement=sql.replace('?','%s')+(' RETURNING id' if returns_id else '')
        try:
            with connection.cursor() as cur:
                cur.execute(statement,params)
                names=[d[0] for d in cur.description] if cur.description else []
                rows=[Row(zip(names,r)) for r in cur.fetchall()] if names else []
                return Result(rows,rows[0]['id'] if returns_id else None)
        except IntegrityError as e:raise sqlite3.IntegrityError('Restricción PostgreSQL') from e
    def __enter__(self):
        self.atomic=transaction.atomic();self.atomic.__enter__();return self
    def __exit__(self,*args):return self.atomic.__exit__(*args)
    def close(self):pass  # Django owns request connection lifecycle.

def connect(_=None):return Database()
