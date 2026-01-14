# application/use_cases/filter_and_aggregate_use_case.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict

import pandas as pd

from application.services.convenio_calendar import ConvenioCalendar
from utils.columns import resolve_column


@dataclass(frozen=True)
class FilterAggregateResult:
    detail_df: pd.DataFrame
    grouped_df: pd.DataFrame


class FilterAndAggregateUseCase:
    def __init__(self, *, calendar: ConvenioCalendar) -> None:
        self._calendar = calendar

    def __call__(self, df: pd.DataFrame, *, dni_to_convenio: Dict[str, str]) -> FilterAggregateResult:
        if df.empty:
            return FilterAggregateResult(detail_df=df, grouped_df=df)

        res_tipo_hora_col = resolve_column(df, "res_tipo_hora")
        mask = df[res_tipo_hora_col].astype(str).str.contains("HORA EXTRA", case=False, na=False)
        detail = df.loc[mask].copy()

        if detail.empty:
            return FilterAggregateResult(detail_df=detail, grouped_df=detail.copy())

        fec_col = resolve_column(detail, "fec")
        can_col = resolve_column(detail, "can")
        dni_col = resolve_column(detail, "dni")
        cod_col = resolve_column(detail, "cod", alternatives=["cod_tipo_hora"])

        # normalización DNI
        detail[dni_col] = detail[dni_col].astype(str).str.strip().str.upper()

        fec_dt = pd.to_datetime(detail[fec_col], errors="coerce")
        dates = fec_dt.dt.date

        def is_festivo_row(d: date, dni: str) -> bool:
            if d is None:
                return False
            convenio = dni_to_convenio.get(dni, self._calendar.default_convenio)
            return self._calendar.is_festivo_o_fin_semana(convenio, d)

        is_festivo = [
            is_festivo_row(d, dni)
            for d, dni in zip(dates.tolist(), detail[dni_col].tolist())
        ]

        detail["festivo"] = detail[can_col].where(pd.Series(is_festivo, index=detail.index), 0)
        detail["laborable"] = detail[can_col].where(~pd.Series(is_festivo, index=detail.index), 0)

        grouped = (
            detail.groupby([dni_col, cod_col], dropna=False, as_index=False)
            .agg(
                res_empleado=("res_empleado", "first"),
                can=(can_col, "sum"),
                festivo=("festivo", "sum"),
                laborable=("laborable", "sum"),
            )
            .rename(columns={dni_col: "dni", cod_col: "cod"})
        )

        return FilterAggregateResult(detail_df=detail, grouped_df=grouped)
