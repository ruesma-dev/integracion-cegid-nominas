# application/use_cases/fill_templates_batch_use_case.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd

from config.config import Config
from application.use_cases.fill_template_excel_use_case import (
    FillTemplateExcelUseCase,
    TemplateFillResult,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchFillResult:
    outputs: List[TemplateFillResult]
    skipped: List[Path]


class FillTemplatesBatchUseCase:
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

        outputs: List[TemplateFillResult] = []
        skipped: List[Path] = []

        for tpl in templates:
            output_path = out_dir / tpl.name

            # 1) Dry-run para saber si habría inserciones
            preview = self._fill_uc(
                template_path=tpl,
                output_path=output_path,
                grouped_df=grouped_df,
                sheet_name=sheet_name,
                save=False,
            )

            # Si no hay ningún trabajador del excel con horas extra => NO generar
            if preview.inserted_rows == 0:
                skipped.append(tpl)
                log.info(
                    "Plantilla omitida (sin horas extra para DNIs del excel): %s | matched=%s | missing=%s",
                    tpl.name,
                    preview.matched_rows,
                    preview.missing_dnis,
                )
                continue

            # 2) Guardado real
            saved = self._fill_uc(
                template_path=tpl,
                output_path=output_path,
                grouped_df=grouped_df,
                sheet_name=sheet_name,
                save=True,
            )
            outputs.append(saved)

            log.info(
                "Plantilla generada: %s -> %s | inserted=%s | matched=%s | missing=%s",
                tpl.name,
                output_path.name,
                saved.inserted_rows,
                saved.matched_rows,
                saved.missing_dnis,
            )

        return BatchFillResult(outputs=outputs, skipped=skipped)
