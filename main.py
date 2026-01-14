# main.py
from __future__ import annotations

import logging
import sys

from application.pipeline import Pipeline, Step
from application.services.convenio_calendar import ConvenioCalendar
from application.use_cases.extract_tables_use_case import ExtractTablesUseCase
from application.use_cases.export_excel_use_case import ExportExcelUseCase
from application.use_cases.filter_and_aggregate_use_case import FilterAndAggregateUseCase
from application.use_cases.fill_template_excel_use_case import FillTemplateExcelUseCase
from application.use_cases.fill_templates_batch_use_case import FillTemplatesBatchUseCase
from application.use_cases.read_worker_convenio_from_templates_use_case import (
    ReadWorkerConvenioFromTemplatesUseCase,
)
from application.use_cases.transform_join_use_case import TransformJoinUseCase
from config.config import Config
from infrastructure.pg_gateway import PostgresGateway


def step_init(ctx: dict) -> dict:
    config = Config()
    config.configure_logging()

    log = logging.getLogger("pg_to_excel")
    log.info("Inicializando gateway PostgreSQL...")

    gateway = PostgresGateway(config=config)
    gateway.test_connection()

    convenio_calendar = ConvenioCalendar.from_config(config)

    ctx["config"] = config
    ctx["gateway"] = gateway

    ctx["extract_uc"] = ExtractTablesUseCase(gateway=gateway, config=config)
    ctx["transform_uc"] = TransformJoinUseCase(config=config)

    ctx["read_convenios_uc"] = ReadWorkerConvenioFromTemplatesUseCase(
        config=config,
        convenio_calendar=convenio_calendar,
    )

    ctx["filter_agg_uc"] = FilterAndAggregateUseCase(calendar=convenio_calendar)

    ctx["export_uc"] = ExportExcelUseCase(config=config)

    fill_one_uc = FillTemplateExcelUseCase()
    ctx["fill_templates_uc"] = FillTemplatesBatchUseCase(config=config, fill_uc=fill_one_uc)

    return ctx


def step_extract(ctx: dict) -> dict:
    ctx["tables"] = ctx["extract_uc"]()
    return ctx


def step_transform(ctx: dict) -> dict:
    ctx["result_df"] = ctx["transform_uc"](ctx["tables"])
    return ctx


def step_read_convenios_from_templates(ctx: dict) -> dict:
    mapping = ctx["read_convenios_uc"]()
    ctx["dni_to_convenio"] = mapping.dni_to_convenio
    ctx["dni_to_ccc"] = mapping.dni_to_ccc
    return ctx


def step_filter_aggregate(ctx: dict) -> dict:
    result = ctx["filter_agg_uc"](ctx["result_df"], dni_to_convenio=ctx["dni_to_convenio"])
    ctx["detail_df"] = result.detail_df
    ctx["grouped_df"] = result.grouped_df
    return ctx


def step_export_detail_and_grouped(ctx: dict) -> dict:
    export_result = ctx["export_uc"](ctx["detail_df"], ctx["grouped_df"])
    ctx["detail_path"] = export_result.detail_path
    ctx["grouped_path"] = export_result.grouped_path
    return ctx


def step_fill_templates_batch(ctx: dict) -> dict:
    result = ctx["fill_templates_uc"](ctx["grouped_df"])
    ctx["template_outputs"] = result.outputs
    ctx["template_skipped"] = result.skipped
    return ctx


def step_close(ctx: dict) -> dict:
    ctx["gateway"].close()
    logging.getLogger("pg_to_excel").info("Conexiones cerradas.")
    return ctx


def main() -> int:
    pipeline = Pipeline(
        Step(step_init, "init"),
        Step(step_extract, "extract"),
        Step(step_transform, "transform"),
        Step(step_read_convenios_from_templates, "read_convenios"),
        Step(step_filter_aggregate, "filter_aggregate"),
        Step(step_export_detail_and_grouped, "export_detail_grouped"),
        Step(step_fill_templates_batch, "fill_templates_batch"),
        Step(step_close, "close"),
    )

    try:
        ctx = pipeline({})
        log = logging.getLogger("pg_to_excel")

        log.info("Excel detalle: %s", ctx["detail_path"])
        log.info("Excel resumen: %s", ctx["grouped_path"])

        outputs = ctx.get("template_outputs", [])
        skipped = ctx.get("template_skipped", [])
        log.info("Plantillas generadas: %s | omitidas: %s", len(outputs), len(skipped))
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        logging.getLogger("pg_to_excel").error("Error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
