# application/use_cases/transform_join_use_case.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd

from config.config import Config
from utils.columns import resolve_column

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BringColumn:
    name: str
    alias: str


@dataclass(frozen=True)
class JoinSpec:
    right_table: str
    left_key: str
    right_key: str
    bring_columns: List[BringColumn]


class TransformJoinUseCase:
    def __init__(self, *, config: Config) -> None:
        self._config = config

    def __call__(self, tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        partes = tables["partes"].copy()
        right_map = {
            "recursos": tables["recursos"].copy(),
            "tipo_hora": tables["tipo_hora"].copy(),
            "empleados": tables["empleados"].copy(),
        }

        joins_cfg = self._config.join_config.joins
        j1 = self._build_spec_from_yaml(joins_cfg, "join_1")
        j2 = self._build_spec_from_yaml(joins_cfg, "join_2")
        j3 = self._build_spec_from_yaml(joins_cfg, "join_3")

        df = self._left_join(df_left=partes, right_map=right_map, spec=j1, join_name="Join 1")
        df = self._left_join(df_left=df, right_map=right_map, spec=j2, join_name="Join 2")
        df = self._left_join(df_left=df, right_map=right_map, spec=j3, join_name="Join 3")

        return df

    def _left_join(
        self,
        *,
        df_left: pd.DataFrame,
        right_map: Dict[str, pd.DataFrame],
        spec: JoinSpec,
        join_name: str,
    ) -> pd.DataFrame:
        right_df = self._get_right_df(right_map, spec.right_table)

        left_key = resolve_column(df_left, spec.left_key)
        right_key = resolve_column(right_df, spec.right_key)

        select_cols = [right_key]
        rename_map: Dict[str, str] = {}

        for bc in spec.bring_columns:
            src = resolve_column(right_df, bc.name)
            select_cols.append(src)
            rename_map[src] = bc.alias

        right_sel = right_df[select_cols].copy()
        right_sel = right_sel.rename(columns=rename_map)

        log.info(
            "%s: left.%s = %s.%s (bring: %s)",
            join_name,
            left_key,
            spec.right_table,
            right_key,
            ", ".join([f"{c.name}->{c.alias}" for c in spec.bring_columns]),
        )

        df = df_left.merge(
            right_sel,
            how="left",
            left_on=left_key,
            right_on=right_key,
            suffixes=("", "_r"),
        )

        # eliminar la clave derecha si no es la misma columna que la izquierda
        if right_key in df.columns and right_key != left_key:
            df = df.drop(columns=[right_key])

        return df

    @staticmethod
    def _get_right_df(right_map: Dict[str, pd.DataFrame], key: str) -> pd.DataFrame:
        if key not in right_map:
            raise KeyError(
                f"right_table='{key}' no soportada. "
                f"Opciones: {', '.join(sorted(right_map.keys()))}"
            )
        return right_map[key]

    @staticmethod
    def _build_spec_from_yaml(joins_cfg: dict, join_key: str) -> JoinSpec:
        if join_key not in joins_cfg:
            raise KeyError(f"Falta '{join_key}' en config/join_config.yaml")

        cfg = joins_cfg[join_key]
        missing = [k for k in ("right_table", "left_key", "right_key", "bring_columns") if k not in cfg]
        if missing:
            raise KeyError(f"En '{join_key}' faltan claves en YAML: {missing}")

        bring = TransformJoinUseCase._parse_bring_columns(cfg["bring_columns"], join_key)

        return JoinSpec(
            right_table=str(cfg["right_table"]),
            left_key=str(cfg["left_key"]),
            right_key=str(cfg["right_key"]),
            bring_columns=bring,
        )

    @staticmethod
    def _parse_bring_columns(raw: object, join_key: str) -> List[BringColumn]:
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"'{join_key}.bring_columns' debe ser una lista no vacía.")

        parsed: List[BringColumn] = []
        for item in raw:
            if isinstance(item, str):
                # permitido: "columna" (alias=columna)
                parsed.append(BringColumn(name=item, alias=item))
                continue

            if isinstance(item, dict):
                if "name" not in item:
                    raise KeyError(f"En '{join_key}.bring_columns' falta 'name' en un elemento dict.")
                name = str(item["name"])
                alias = str(item.get("alias", name))
                parsed.append(BringColumn(name=name, alias=alias))
                continue

            raise TypeError(
                f"Elemento inválido en '{join_key}.bring_columns': {item!r}. "
                f"Usa string o dict con 'name' y opcional 'alias'."
            )

        return parsed
