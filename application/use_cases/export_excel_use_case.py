# application/use_cases/export_excel_use_case.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import pandas as pd

from config.config import Config

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExcelExportResult:
    detail_path: Path
    grouped_path: Path


class ExportExcelUseCase:
    def __init__(self, *, config: Config) -> None:
        self._config = config

    def __call__(self, detail_df: pd.DataFrame, grouped_df: pd.DataFrame) -> ExcelExportResult:
        detail_path = self._config.output_path_detail()
        grouped_path = self._config.output_path_grouped()

        log.info("Escribiendo Excel detalle: %s", detail_path)
        with pd.ExcelWriter(detail_path, engine="openpyxl") as writer:
            detail_df.to_excel(writer, sheet_name="detalle", index=False)

        log.info("Escribiendo Excel resumen: %s", grouped_path)
        with pd.ExcelWriter(grouped_path, engine="openpyxl") as writer:
            grouped_df.to_excel(writer, sheet_name="resumen", index=False)

        log.info(
            "Excels generados. Detalle=%s filas; Resumen=%s filas.",
            len(detail_df),
            len(grouped_df),
        )
        return ExcelExportResult(detail_path=detail_path, grouped_path=grouped_path)
