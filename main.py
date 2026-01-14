# main.py
from __future__ import annotations

import logging
import sys

from application.pipeline import Pipeline, Step
from application.services.calendar_laboral import CalendarLaboral
from application.use_cases.extract_tables_use_case import ExtractTablesUseCase
from application.use_cases.filter_and_aggregate_use_case import FilterAndAggregateUseCase
from application.use_cases.fill_template_excel_use_case import FillTemplateExcelUseCase
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

    calendar = CalendarLaboral.from_config(config)

    ctx["config"] = config
    ctx["gateway"] = gateway

    ctx["extract_uc"] = ExtractTablesUseCase(gateway=gateway, config=config)
    ctx["transform_uc"] = TransformJoinUseCase(config=config)
    ctx["filter_agg_uc"] = FilterAndAggregateUseCase(calendar=calendar)
    ctx["fill_template_uc"] = FillTemplateExcelUseCase(config=config)

    return ctx


def step_extract(ctx: dict) -> dict:
    extract_uc: ExtractTablesUseCase = ctx["extract_uc"]
    ctx["tables"] = extract_uc()
    return ctx


def step_transform(ctx: dict) -> dict:
    transform_uc: TransformJoinUseCase = ctx["transform_uc"]
    ctx["result_df"] = transform_uc(ctx["tables"])
    return ctx


def step_filter_aggregate(ctx: dict) -> dict:
    uc: FilterAndAggregateUseCase = ctx["filter_agg_uc"]
    result = uc(ctx["result_df"])
    ctx["detail_df"] = result.detail_df
    ctx["grouped_df"] = result.grouped_df
    return ctx


def step_fill_template(ctx: dict) -> dict:
    uc: FillTemplateExcelUseCase = ctx["fill_template_uc"]
    result = uc(ctx["grouped_df"])
    ctx["output_path"] = result.output_path
    ctx["filled_rows"] = result.filled_rows
    ctx["missing_dnis"] = result.missing_dnis
    return ctx


def step_close(ctx: dict) -> dict:
    gateway: PostgresGateway = ctx["gateway"]
    gateway.close()
    logging.getLogger("pg_to_excel").info("Conexiones cerradas.")
    return ctx


def main() -> int:
    pipeline = Pipeline(
        Step(step_init, "init"),
        Step(step_extract, "extract"),
        Step(step_transform, "transform"),
        Step(step_filter_aggregate, "filter_aggregate"),
        Step(step_fill_template, "fill_template"),
        Step(step_close, "close"),
    )

    try:
        ctx = pipeline({})
        log = logging.getLogger("pg_to_excel")
        log.info("Salida generada: %s", ctx["output_path"])
        log.info("Filas actualizadas: %s | DNIs sin datos: %s", ctx["filled_rows"], ctx["missing_dnis"])
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        logging.getLogger("pg_to_excel").error("Error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
