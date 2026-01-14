# application/services/convenio_calendar.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Set

from config.config import Config


@dataclass(frozen=True)
class ConvenioCalendar:
    default_convenio: str
    ccc_to_convenio: Dict[str, str]
    holidays: Dict[str, Dict[int, Set[date]]]  # convenio -> year -> set(date)

    @classmethod
    def from_config(cls, config: Config) -> "ConvenioCalendar":
        cfg = config.join_config.convenios or {}

        default_convenio = str(cfg.get("default", "")).strip()
        ccc_to_convenio = {str(k): str(v) for k, v in (cfg.get("ccc_to_convenio", {}) or {}).items()}

        calendars = cfg.get("calendars", {}) or {}
        holidays: Dict[str, Dict[int, Set[date]]] = {}

        for convenio_name, convenio_cfg in calendars.items():
            years_cfg = (convenio_cfg or {}).get("holidays_by_year", {}) or {}
            per_year: Dict[int, Set[date]] = {}
            for year_str, dates_list in years_cfg.items():
                year = int(year_str)
                per_year[year] = set(date(int(s.split("-")[0]), int(s.split("-")[1]), int(s.split("-")[2]))
                                    for s in (dates_list or []))
            holidays[str(convenio_name)] = per_year

        if not default_convenio:
            # fallback: primer convenio definido, si existe
            default_convenio = next(iter(holidays.keys()), "")

        return cls(
            default_convenio=default_convenio,
            ccc_to_convenio=ccc_to_convenio,
            holidays=holidays,
        )

    @staticmethod
    def is_weekend(d: date) -> bool:
        return d.weekday() >= 5

    def convenio_for_ccc(self, ccc: str) -> str:
        return self.ccc_to_convenio.get(str(ccc), self.default_convenio)

    def is_holiday(self, convenio: str, d: date) -> bool:
        return d in self.holidays.get(convenio, {}).get(d.year, set())

    def is_festivo_o_fin_semana(self, convenio: str, d: date) -> bool:
        return self.is_weekend(d) or self.is_holiday(convenio, d)
