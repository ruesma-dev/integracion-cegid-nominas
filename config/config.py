# config/config.py
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class JoinConfig:
    raw: dict

    @property
    def tables(self) -> dict:
        return self.raw.get("tables", {})

    @property
    def joins(self) -> dict:
        return self.raw.get("joins", {})

    @property
    def extract(self) -> dict:
        return self.raw.get("extract", {})

    @property
    def calendar(self) -> dict:
        return self.raw.get("calendar", {})

    @property
    def templates(self) -> dict:
        return self.raw.get("templates", {})


class Config:
    def __init__(self) -> None:
        load_dotenv()

        self.pg_server = os.getenv("PG_SERVER", "").strip()
        self.pg_port = int(os.getenv("PG_PORT", "5432").strip())
        self.pg_database = os.getenv("PG_DATABASE", "").strip()
        self.pg_user = os.getenv("PG_USER", "").strip()
        self.pg_password = os.getenv("PG_PASSWORD", "").strip()
        self.pg_schema = os.getenv("PG_SCHEMA", "public").strip()

        self.output_dir = os.getenv("OUTPUT_DIR", "output").strip()

        # Estos dos se mantienen (detalle/resumen) sin cambios en tu lógica previa
        self.output_detail_filename = os.getenv("OUTPUT_FILENAME", "export_horas_extra_detalle.xlsx").strip()
        self.output_grouped_filename = os.getenv("OUTPUT_FILENAME_GROUPED", "export_horas_extra_resumen.xlsx").strip()

        self.log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        self._join_config = self._load_join_config()

    def configure_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, self.log_level, logging.INFO),
            format="%(asctime)s  [%(levelname)s]  %(name)s: %(message)s",
            handlers=[logging.StreamHandler()],
        )

    @property
    def join_config(self) -> JoinConfig:
        return self._join_config

    def output_path_detail(self) -> Path:
        out_dir = Path(self.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / self.output_detail_filename

    def output_path_grouped(self) -> Path:
        out_dir = Path(self.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / self.output_grouped_filename

    def output_templates_dir(self) -> Path:
        subdir = (self.join_config.templates or {}).get("output_subdir", "plantillas")
        out_dir = Path(self.output_dir) / str(subdir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    @staticmethod
    def _load_join_config() -> JoinConfig:
        cfg_path = Path("config") / "join_config.yaml"
        if not cfg_path.exists():
            raise FileNotFoundError(f"No existe {cfg_path}. Revisa el proyecto.")

        with cfg_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        return JoinConfig(raw=raw)
