# infrastructure/pg_gateway.py
from __future__ import annotations

import logging
from typing import Optional, Iterable, Dict, Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

from config.config import Config

log = logging.getLogger(__name__)


class PostgresGateway:
    def __init__(self, *, config: Config) -> None:
        self._config = config
        self._engine: Optional[Engine] = None
        self._conn: Optional[Connection] = None
        self._ensure_engine()

    def _ensure_engine(self) -> None:
        if self._engine is not None:
            return

        url = (
            f"postgresql+psycopg2://{self._config.pg_user}:{self._config.pg_password}"
            f"@{self._config.pg_server}:{self._config.pg_port}/{self._config.pg_database}"
        )
        self._engine = create_engine(url, future=True, pool_pre_ping=True)
        self._conn = self._engine.connect()

    def test_connection(self) -> None:
        if self._conn is None:
            raise RuntimeError("Conexión no inicializada.")
        row = self._conn.execute(text("SELECT 1")).scalar()
        if row != 1:
            raise RuntimeError("SELECT 1 devolvió un valor inesperado.")
        log.info("Conexión a PostgreSQL OK (db=%s).", self._config.pg_database)

    def read_table(
        self,
        table: str,
        columns: Optional[Iterable[str]] = None,
        where_sql: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        if self._conn is None:
            raise RuntimeError("Conexión no inicializada.")

        schema = self._config.pg_schema
        if columns:
            cols = ", ".join([f'"{c}"' for c in columns])
        else:
            cols = "*"

        sql_str = f'SELECT {cols} FROM "{schema}"."{table}"'
        if where_sql:
            sql_str = f"{sql_str} WHERE {where_sql}"

        log.info("Extrayendo tabla %s.%s ...", schema, table)

        # CLAVE: usar sqlalchemy.text() para que :params se binden correctamente
        stmt = text(sql_str)
        df = pd.read_sql_query(stmt, self._conn, params=params)

        log.info("Tabla %s: %s filas.", table, len(df))
        return df

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
