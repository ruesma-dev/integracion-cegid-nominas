# utils/columns.py
from __future__ import annotations

import re
from typing import Iterable, Optional

import pandas as pd


def _norm(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"\s+", "", s)
    s = s.replace("_", "")
    s = s.replace("-", "")
    return s


def resolve_column(df: pd.DataFrame, desired: str, *, alternatives: Optional[Iterable[str]] = None) -> str:
    """
    Resuelve un nombre de columna por normalización para tolerar:
    - espacios vs underscores
    - mayúsculas/minúsculas
    - pequeños cambios de formato

    Si no se encuentra, lanza KeyError con detalle.
    """
    desired_norm = _norm(desired)
    alt = list(alternatives or [])
    candidates = [desired] + alt

    norm_map = {_norm(c): c for c in df.columns}
    for cand in candidates:
        key = _norm(cand)
        if key in norm_map:
            return norm_map[key]

    available = ", ".join(df.columns.astype(str).tolist())
    raise KeyError(f"No se encontró columna '{desired}' (ni alternativas) en DF. Columnas disponibles: {available}")
