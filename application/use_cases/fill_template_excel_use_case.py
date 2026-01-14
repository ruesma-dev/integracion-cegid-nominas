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

log = logging.getLogger(__name__)

DNI_RE = re.compile(r"^[0-9]{8}[A-Z]$|^[XYZ][0-9]{7}[A-Z]$", re.IGNORECASE)


@dataclass(frozen=True)
class TemplateFillResult:
    output_path: Path
    matched_rows: int        # DNIs del excel que existen en hours_by_dni
    inserted_rows: int       # DNIs del excel con horas > 0 (se escriben)
    missing_dnis: int        # DNIs del excel sin datos en hours_by_dni


class FillTemplateExcelUseCase:
    """
    Rellena UNA plantilla Excel preservando formato.
    Guarda el archivo SOLO si el caller lo decide; este UC devuelve métricas.
    """

    def __call__(
        self,
        *,
        template_path: Path,
        output_path: Path,
        grouped_df: pd.DataFrame,
        sheet_name: str = "",
        save: bool = True,
    ) -> TemplateFillResult:
        if not template_path.exists():
            raise FileNotFoundError(f"No existe la plantilla: {template_path}")

        hours_by_dni = self._build_hours_by_dni(grouped_df)

        wb = load_workbook(template_path)
        ws = self._select_sheet(wb, sheet_name)

        header_row, col_nif, col_normal, col_festiva = self._find_header(ws)

        matched = 0
        inserted = 0
        missing = 0

        for r in range(header_row + 1, ws.max_row + 1):
            nif_val = ws.cell(row=r, column=col_nif).value
            nif = self._normalize_dni(nif_val)
            if not nif:
                continue

            if nif not in hours_by_dni:
                missing += 1
                continue

            matched += 1
            normal, festiva = hours_by_dni[nif]

            # Solo escribimos si hay horas > 0 en alguno
            if (normal or 0) > 0 or (festiva or 0) > 0:
                ws.cell(row=r, column=col_normal).value = float(normal)
                ws.cell(row=r, column=col_festiva).value = float(festiva)
                inserted += 1

        if save:
            wb.save(output_path)

        return TemplateFillResult(
            output_path=output_path,
            matched_rows=matched,
            inserted_rows=inserted,
            missing_dnis=missing,
        )

    @staticmethod
    def _build_hours_by_dni(grouped_df: pd.DataFrame) -> Dict[str, Tuple[float, float]]:
        required = {"dni", "laborable", "festivo"}
        missing = required - set(grouped_df.columns)
        if missing:
            raise KeyError(f"Faltan columnas en grouped_df: {sorted(missing)}")

        df = grouped_df.copy()
        df["dni"] = df["dni"].astype(str).str.strip().str.upper()

        agg = df.groupby("dni", as_index=False)[["laborable", "festivo"]].sum()

        out: Dict[str, Tuple[float, float]] = {}
        for _, row in agg.iterrows():
            out[str(row["dni"]).upper()] = (float(row["laborable"]), float(row["festivo"]))
        return out

    @staticmethod
    def _select_sheet(wb, sheet_name: str):
        if sheet_name:
            if sheet_name not in wb.sheetnames:
                raise KeyError(f"Hoja '{sheet_name}' no existe. Hojas disponibles: {wb.sheetnames}")
            return wb[sheet_name]
        return wb.active

    @staticmethod
    def _find_header(ws: Worksheet):
        target = {"NIF", "Num Hora Extra Normal", "Num Hora Extra Festiva"}
        max_scan = min(ws.max_row, 200)
        for r in range(1, max_scan + 1):
            row_vals = {}
            for c in range(1, ws.max_column + 1):
                v = ws.cell(row=r, column=c).value
                if v is None:
                    continue
                row_vals[str(v).strip()] = c

            if target.issubset(row_vals.keys()):
                return (
                    r,
                    row_vals["NIF"],
                    row_vals["Num Hora Extra Normal"],
                    row_vals["Num Hora Extra Festiva"],
                )

        raise RuntimeError(
            "No se encontró cabecera con 'NIF', 'Num Hora Extra Normal' y 'Num Hora Extra Festiva'."
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
