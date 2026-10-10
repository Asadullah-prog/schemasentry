"""Dataset profiling: observed statistics and conservative type inference.

Statistics are *observed* from the data; ``inferred_type`` is a best-effort
guess and is always labeled as such — inference is not guaranteed correct.
"""

from __future__ import annotations

import statistics
from typing import Any

from schemasentry.readers import Dataset
from schemasentry.validator import coerce

_TYPE_PRECEDENCE = ("integer", "float", "boolean", "date")


def infer_type(values: list[str]) -> str:
    """Infer the most specific type satisfied by every non-missing value."""
    if not values:
        return "string"
    for candidate in _TYPE_PRECEDENCE:
        if all(coerce(v, candidate)[0] for v in values):
            return candidate
    return "string"


def profile(dataset: Dataset) -> dict[str, Any]:
    """Compute a JSON-serializable profile of ``dataset``."""
    columns: list[dict[str, Any]] = []
    seen_rows: set[tuple] = set()
    duplicate_rows = 0

    for row in dataset.rows:
        key = tuple(row.get(c) for c in dataset.columns)
        if key in seen_rows:
            duplicate_rows += 1
        else:
            seen_rows.add(key)

    for name in dataset.columns:
        raw_values = [row.get(name) for row in dataset.rows]
        missing = [v for v in raw_values if v is None]
        present = [v for v in raw_values if v is not None]
        inferred = infer_type(present)
        entry: dict[str, Any] = {
            "name": name,
            "inferred_type": inferred,
            "missing_count": len(missing),
            "missing_pct": round(len(missing) / len(raw_values) * 100, 2) if raw_values else 0.0,
            "distinct_count": len(set(present)),
        }
        if inferred in ("integer", "float") and present:
            numbers = [coerce(v, inferred)[1] for v in present]
            entry["min"] = min(numbers)
            entry["max"] = max(numbers)
            entry["mean"] = statistics.fmean(numbers)
            entry["median"] = statistics.median(numbers)
        columns.append(entry)

    return {
        "dataset": dataset.source,
        "format": dataset.format,
        "sheet": dataset.sheet,
        "row_count": dataset.row_count,
        "column_count": len(dataset.columns),
        "duplicate_rows": duplicate_rows,
        "columns": columns,
        "note": (
            "inferred_type values are best-effort guesses from observed data, "
            "not guarantees. Review before encoding them in a contract."
        ),
    }
