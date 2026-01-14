# application/services/calendar_laboral.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Set

from config.config import Config


@dataclass(frozen=True)
class CalendarLaboral:
    holidays_by_year: Dict[int, Set[date]]

    @classmethod
    def from_config(cls, config: Config) -> "CalendarLaboral":
        raw = config.join_config.calendar or {}
        by_year = raw.get("holidays_by_year", {}) or {}

        parsed: Dict[int, Set[date]] = {}
        for year_str, dates_list in by_year.items():
            year = int(year_str)
            holidays: Set[date] = set()
            for s in dates_list or []:
                y, m, d = (int(p) for p in str(s).split("-"))
                holidays.add(date(y, m, d))
            parsed[year] = holidays

        return cls(holidays_by_year=parsed)

    @staticmethod
    def is_weekend(d: date) -> bool:
        return d.weekday() >= 5  # 5=sábado, 6=domingo

    def is_holiday(self, d: date) -> bool:
        return d in self.holidays_by_year.get(d.year, set())

    def is_festivo_o_fin_semana(self, d: date) -> bool:
        return self.is_weekend(d) or self.is_holiday(d)
