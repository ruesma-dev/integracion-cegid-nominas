# application/use_cases/filter_and_aggregate_use_case.py
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from application.services.calendar_laboral import CalendarLaboral
from utils.columns import resolve_column


@dataclass(frozen=True)
class FilterAggregateResult:
    detail_df: pd.DataFrame
    grouped_df: pd.DataFrame


class FilterAndAggregateUseCase:
    """
    1) Filtra filas donde res_tipo_hora contiene 'HORA EXTRA'
    2) Crea columnas 'festivo' y 'laborable' (según fec y calendario)
    3) Agrupa por DNI y cod, sumando can (y también festivo/laborable)
    """

    def __init__(self, *, calendar: CalendarLaboral) -> None:
        self._calendar = calendar

    def __call__(self, df: pd.DataFrame) -> FilterAggregateResult:
        if df.empty:
            return FilterAggregateResult(detail_df=df, grouped_df=df)

        res_tipo_hora_col = resolve_column(df, "res_tipo_hora")
        mask = df[res_tipo_hora_col].astype(str).str.contains("HORA EXTRA", case=False, na=False)
        detail = df.loc[mask].copy()

        if detail.empty:
            return FilterAggregateResult(detail_df=detail, grouped_df=detail.copy())

        # columnas base
        fec_col = resolve_column(detail, "fec")
        can_col = resolve_column(detail, "can")
        dni_col = resolve_column(detail, "dni")
        cod_col = self._resolve_cod(detail)

        # aseguramos res_empleado (para el excel detalle)
        # si no existiera, explotará aquí con un error claro
        _ = resolve_column(detail, "res_empleado")

        # normaliza fecha (date) desde timestamp
        fec_dt = pd.to_datetime(detail[fec_col], errors="coerce")
        dates = fec_dt.dt.date

        is_festivo = dates.apply(
            lambda d: False if d is None else self._calendar.is_festivo_o_fin_semana(d)
        )

        # columnas nuevas
        detail["festivo"] = detail[can_col].where(is_festivo, 0)
        detail["laborable"] = detail[can_col].where(~is_festivo, 0)

        res_empleado_col = resolve_column(detail, "res_empleado")

        grouped = (
            detail.groupby([dni_col, cod_col], dropna=False, as_index=False)
            .agg(
                res_empleado=(res_empleado_col, "first"),
                can=("{}".format(can_col), "sum"),
                festivo=("festivo", "sum"),
                laborable=("laborable", "sum"),
            )
            .rename(columns={dni_col: "dni", cod_col: "cod"})
        )

        return FilterAggregateResult(detail_df=detail, grouped_df=grouped)

    @staticmethod
    def _resolve_cod(df: pd.DataFrame) -> str:
        return resolve_column(
            df,
            "cod",
            alternatives=["cod_tipo_hora", "codtipohora", "codtipo_hora"],
        )
