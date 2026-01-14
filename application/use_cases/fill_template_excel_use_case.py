# application/use_cases/fill_template_excel_use_case.py
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional

import pandas as pd
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from config.config import Config

log = logging.getLogger(__name__)

DNI_RE = re.compile(r"^[0-9]{8}[A-Z]$|^[XYZ][0-9]{7}[A-Z]$", re.IGNORECASE)


@dataclass(frozen=True)
class TemplateFillResult:
    output_path: Path
    filled_rows: int
    missing_dnis: int


class FillTemplateExcelUseCase:
    """
    Rellena input/base.xlsx preservando formato:
    - Casar filas por 'NIF' (DNI/NIE)
    - Escribir:
        Num Hora Extra Normal  <- laborable
        Num Hora Extra Festiva <- festivo
    """

    def __init__(self, *, config: Config) -> None:
        self._config = config

    def __call__(self, grouped_df: pd.DataFrame) -> TemplateFillResult:
        template_path = self._config.input_template_path()
        if not template_path.exists():
            raise FileNotFoundError(f"No existe la plantilla: {template_path}")

        output_path = self._config.output_path_template()

        # aggregated per DNI (porque grouped_df puede venir por dni+cod)
        hours_by_dni = self._build_hours_by_dni(grouped_df)

        wb = load_workbook(template_path)
        ws = self._select_sheet(wb)

        header_row, col_nif, col_normal, col_festiva = self._find_header(ws)

        filled = 0
        missing = 0

        for r in range(header_row + 1, ws.max_row + 1):
            nif_val = ws.cell(row=r, column=col_nif).value
            nif = self._normalize_dni(nif_val)
            if not nif:
                continue

            if nif not in hours_by_dni:
                missing += 1
                continue

            normal, festiva = hours_by_dni[nif]

            # Escribir valores (numéricos). Si quieres formato específico, se define en plantilla.
            ws.cell(row=r, column=col_normal).value = float(normal)
            ws.cell(row=r, column=col_festiva).value = float(festiva)
            filled += 1

        wb.save(output_path)
        log.info("Plantilla rellenada. Filas actualizadas=%s, dnis sin datos=%s", filled, missing)

        return TemplateFillResult(output_path=output_path, filled_rows=filled, missing_dnis=missing)

    @staticmethod
    def _build_hours_by_dni(grouped_df: pd.DataFrame) -> Dict[str, Tuple[float, float]]:
        """
        Espera columnas:
          - dni
          - laborable
          - festivo
        Si hay más granularidad (dni+cod), se suma.
        """
        required = {"dni", "laborable", "festivo"}
        missing = required - set(grouped_df.columns)
        if missing:
            raise KeyError(f"Faltan columnas en grouped_df para rellenar plantilla: {sorted(missing)}")

        df = grouped_df.copy()
        df["dni"] = df["dni"].astype(str).str.strip().str.upper()

        agg = (
            df.groupby("dni", as_index=False)[["laborable", "festivo"]]
            .sum()
        )

        out: Dict[str, Tuple[float, float]] = {}
        for _, row in agg.iterrows():
            out[str(row["dni"]).upper()] = (float(row["laborable"]), float(row["festivo"]))
        return out

    def _select_sheet(self, wb):
        if self._config.template_sheet:
            if self._config.template_sheet not in wb.sheetnames:
                raise KeyError(
                    f"TEMPLATE_SHEET='{self._config.template_sheet}' no existe. "
                    f"Hojas disponibles: {wb.sheetnames}"
                )
            return wb[self._config.template_sheet]
        return wb.active

    @staticmethod
    def _find_header(ws: Worksheet) -> Tuple[int, int, int, int]:
        """
        Busca una fila que contenga las cabeceras:
          - NIF
          - Num Hora Extra Normal
          - Num Hora Extra Festiva
        Escanea las primeras 200 filas para ser robustos.
        """
        target = {
            "NIF": None,
            "Num Hora Extra Normal": None,
            "Num Hora Extra Festiva": None,
        }

        max_scan = min(ws.max_row, 200)
        for r in range(1, max_scan + 1):
            row_vals = {}
            for c in range(1, ws.max_column + 1):
                v = ws.cell(row=r, column=c).value
                if v is None:
                    continue
                s = str(v).strip()
                row_vals[s] = c

            if all(k in row_vals for k in target.keys()):
                return r, row_vals["NIF"], row_vals["Num Hora Extra Normal"], row_vals["Num Hora Extra Festiva"]

        raise RuntimeError(
            "No se encontró la fila de cabecera con 'NIF', 'Num Hora Extra Normal' y 'Num Hora Extra Festiva'. "
            "Revisa la plantilla base.xlsx."
        )

    @staticmethod
    def _normalize_dni(value: object) -> Optional[str]:
        if value is None:
            return None
        s = str(value).strip().upper()
        if not s:
            return None
        if DNI_RE.match(s):
            return s
        return None
