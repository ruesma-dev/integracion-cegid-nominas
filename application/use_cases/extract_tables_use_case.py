# application/use_cases/extract_tables_use_case.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, Tuple

import pandas as pd

from config.config import Config
from infrastructure.pg_gateway import PostgresGateway


class ExtractTablesUseCase:
    def __init__(self, *, gateway: PostgresGateway, config: Config) -> None:
        self._gateway = gateway
        self._config = config

    def __call__(self) -> Dict[str, pd.DataFrame]:
        tables_cfg = self._config.join_config.tables
        extract_cfg = self._config.join_config.extract

        partes_name = tables_cfg.get("partes", "DimPartesTrabajoDetalle")
        recursos_name = tables_cfg.get("recursos", "DimRecursos")
        tipo_hora_name = tables_cfg.get("tipo_hora", "DimTipoHora")
        empleados_name = tables_cfg.get("empleados", "DimEmpleados")

        partes_filter = extract_cfg.get("partes_filter", None)

        where_sql = None
        params = None
        if partes_filter:
            col = str(partes_filter.get("column", "fec"))
            year = int(partes_filter["year"])
            month = int(partes_filter["month"])

            start_dt, end_exclusive = self._period_16_to_15(year, month)

            where_sql = f'"{col}" >= :start_dt AND "{col}" < :end_dt'
            params = {"start_dt": start_dt, "end_dt": end_exclusive}

        partes = self._gateway.read_table(
            partes_name,
            where_sql=where_sql,
            params=params,
        )
        recursos = self._gateway.read_table(recursos_name)
        tipo_hora = self._gateway.read_table(tipo_hora_name)
        empleados = self._gateway.read_table(empleados_name)

        return {
            "partes": partes,
            "recursos": recursos,
            "tipo_hora": tipo_hora,
            "empleados": empleados,
        }

    @staticmethod
    def _period_16_to_15(year: int, month: int) -> Tuple[datetime, datetime]:
        if month < 1 or month > 12:
            raise ValueError(f"month inválido: {month}. Debe estar entre 1 y 12.")

        # inicio: 16 del mes anterior
        if month == 1:
            start = datetime(year - 1, 12, 16)
        else:
            start = datetime(year, month - 1, 16)

        # fin exclusivo: 16 del mes indicado
        end_exclusive = datetime(year, month, 16)
        return start, end_exclusive
