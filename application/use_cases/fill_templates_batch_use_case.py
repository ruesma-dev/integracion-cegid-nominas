# application/use_cases/fill_templates_batch_use_case.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd

from config.config import Config
from application.use_cases.fill_template_excel_use_case import FillTemplateExcelUseCase, TemplateFillResult

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchFillResult:
    outputs: List[TemplateFillResult]


class FillTemplatesBatchUseCase:
    """
    Lee múltiples plantillas en input_dir/pattern y genera una salida por cada una.
    """

    def __init__(self, *, config: Config, fill_uc: FillTemplateExcelUseCase) -> None:
        self._config = config
        self._fill_uc = fill_uc

    def __call__(self, grouped_df: pd.DataFrame) -> BatchFillResult:
        tpl_cfg = self._config.join_config.templates or {}
        input_dir = Path(str(tpl_cfg.get("input_dir", "input")))
        pattern = str(tpl_cfg.get("pattern", "*.xlsx"))
        sheet_name = str(tpl_cfg.get("sheet", "") or "")

        if not input_dir.exists():
            raise FileNotFoundError(f"No existe input_dir de plantillas: {input_dir}")

        templates = sorted(input_dir.glob(pattern))
        if not templates:
            raise FileNotFoundError(f"No se encontraron plantillas en {input_dir} con patrón '{pattern}'")

        out_dir = self._config.output_templates_dir()
        results: List[TemplateFillResult] = []

        for tpl in templates:
            output_path = out_dir / tpl.name  # mismo nombre en output/plantillas
            res = self._fill_uc(
                template_path=tpl,
                output_path=output_path,
                grouped_df=grouped_df,
                sheet_name=sheet_name,
            )
            results.append(res)
            log.info(
                "Plantilla procesada: %s -> %s | filas=%s | dnis_sin_datos=%s",
                tpl.name,
                output_path.name,
                res.filled_rows,
                res.missing_dnis,
            )

        return BatchFillResult(outputs=results)
