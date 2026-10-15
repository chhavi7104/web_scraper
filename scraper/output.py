"""Writers for JSON and CSV."""
from __future__ import annotations

import csv
import json
from typing import Iterable, List

from .models import Company, fields_for_level


def _flat(v) -> str:
    if isinstance(v, dict):
        return "; ".join(f"{k}: {x}" for k, x in v.items())
    if isinstance(v, list):
        return "; ".join(map(str, v))
    return "" if v is None else str(v)


def write_json(companies: Iterable[Company], failures: List[dict], path: str, level: int = 3) -> None:
    companies = list(companies)
    payload = {"count": len(companies), "level": level,
               "companies": [c.to_dict(level) for c in companies], "failures": failures}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def write_csv(companies: Iterable[Company], path: str, level: int = 3) -> None:
    cols = fields_for_level(level)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for c in companies:
            d = c.to_dict(level)
            w.writerow({k: _flat(d[k]) for k in cols})
