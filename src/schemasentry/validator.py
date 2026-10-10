"""Validation engine: checks a Dataset against a Contract.

This module has no CLI or terminal dependencies. ``validate`` returns a
:class:`ValidationReport` describing every rule outcome. Reports never contain
raw cell values — violations carry rule names, counts, and row numbers only.
"""

from __future__ import annotations

import datetime as _datetime
import re
from dataclasses import dataclass, field
from typing import Any

from schemasentry.contract import Contract
from schemasentry.readers import Dataset

_MISSING_SENTINEL = object()
_EXAMPLE_ROW_LIMIT = 5


@dataclass
class Violation:
    """One failed rule, aggregated over all offending rows."""

    rule: str  # e.g. "type", "nullable", "unique", "regex", ...
    column: str | None
    message: str  # actionable explanation; never contains cell values
    count: int = 1
    example_rows: list[int] = field(default_factory=list)  # 1-based data rows
    severity: str = "error"  # "error" | "warning"


@dataclass
class ValidationReport:
    dataset: str
    contract: str
    row_count: int
    passed: bool = True
    violations: list[Violation] = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0
    column_summaries: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "warning"]

    @property
    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "error"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "passed" if self.passed else "failed",
            "dataset": self.dataset,
            "contract": self.contract,
            "row_count": self.row_count,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "violations": [
                {
                    "rule": v.rule,
                    "column": v.column,
                    "severity": v.severity,
                    "message": v.message,
                    "count": v.count,
                    "example_rows": v.example_rows,
                }
                for v in self.violations
            ],
            "column_summaries": self.column_summaries,
        }


_INTEGER_RE = re.compile(r"^[+-]?\d+$")
_BOOLEAN_TRUE = {"true", "1", "yes"}
_BOOLEAN_FALSE = {"false", "0", "no"}


def coerce(value: str, declared: str) -> tuple[bool, Any]:
    """Check whether a raw string value satisfies a declared column type.

    Returns ``(ok, parsed)``. All inputs are strings at this stage, so
    ``integer`` means "parses as an integer", not "is a Python int".
    """
    if declared == "string":
        return True, value
    if declared == "integer":
        if _INTEGER_RE.match(value.strip()):
            try:
                return True, int(value.strip())
            except ValueError:
                pass
        return False, None
    if declared == "float":
        try:
            return True, float(value.strip())
        except ValueError:
            return False, None
    if declared == "boolean":
        lowered = value.strip().lower()
        if lowered in _BOOLEAN_TRUE:
            return True, True
        if lowered in _BOOLEAN_FALSE:
            return True, False
        return False, None
    if declared == "date":
        try:
            return True, _datetime.date.fromisoformat(value.strip())
        except ValueError:
            return False, None
    return False, None  # unreachable for validated contracts


class _Aggregator:
    """Collects per-(rule, column) failures without storing cell values."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str | None], Violation] = {}

    def add(
        self,
        rule: str,
        column: str | None,
        message: str,
        row: int | None = None,
        severity: str = "error",
    ) -> None:
        key = (rule, column)
        entry = self._entries.get(key)
        if entry is None:
            entry = Violation(rule=rule, column=column, message=message, severity=severity)
            self._entries[key] = entry
        else:
            entry.count += 1
            if entry.severity == "error" and severity == "warning":
                pass  # keep the more severe label once aggregated
        if row is not None and len(entry.example_rows) < _EXAMPLE_ROW_LIMIT:
            entry.example_rows.append(row)

    def finalize_counts(self) -> None:
        for entry in self._entries.values():
            if entry.count > 1:
                entry.message = entry.message.replace("1 value(s)", f"{entry.count} value(s)")
                entry.message = entry.message.replace("1 duplicate", f"{entry.count} duplicate")

    def violations(self) -> list[Violation]:
        self.finalize_counts()
        return sorted(
            self._entries.values(), key=lambda v: (v.severity != "error", v.column or "", v.rule)
        )

    def failing_keys(self) -> set[tuple[str, str | None]]:
        return {k for k, v in self._entries.items() if v.severity == "error"}


def _is_missing(value: str | None, missing_values: list[str]) -> bool:
    return value is None or value in missing_values


def validate(dataset: Dataset, contract: Contract, contract_path: str = "") -> ValidationReport:
    """Validate ``dataset`` against ``contract`` and return a full report."""
    agg = _Aggregator()
    checks: dict[tuple[str, str | None], int] = {}

    def check(rule: str, column: str | None) -> None:
        checks[(rule, column)] = checks.get((rule, column), 0) + 1

    dataset_columns = dataset.columns

    # --- required / missing columns ---
    for name, column_rule in contract.columns.items():
        check("column_present", name)
        if name not in dataset_columns and column_rule.required:
            agg.add(
                "column_present",
                name,
                f"Column '{name}': required column is missing from the dataset.",
            )

    # --- unexpected columns ---
    for name in dataset_columns:
        if name not in contract.columns:
            check("extra_column", name)
            message = (
                f"Column '{name}': unexpected column not defined in the contract "
                f"(strictness.extra_columns={contract.extra_columns!r})."
            )
            if contract.extra_columns == "error":
                agg.add("extra_column", name, message, severity="error")
            elif contract.extra_columns == "warn":
                agg.add("extra_column", name, message, severity="warning")
            # "ignore": no record

    # --- row counts ---
    if contract.min_rows is not None:
        check("min_rows", None)
        if dataset.row_count < contract.min_rows:
            agg.add(
                "min_rows",
                None,
                f"Dataset has {dataset.row_count} row(s); contract requires at least "
                f"{contract.min_rows}.",
            )
    if contract.max_rows is not None:
        check("max_rows", None)
        if dataset.row_count > contract.max_rows:
            agg.add(
                "max_rows",
                None,
                f"Dataset has {dataset.row_count} row(s); contract allows at most "
                f"{contract.max_rows}.",
            )

    # --- per-column, per-row rules ---
    missing_sets = {name: set(contract.missing_values) for name in contract.columns}
    seen_unique: dict[str, dict[str, int]] = {
        name: {} for name, rule in contract.columns.items() if rule.unique
    }

    for row_idx, row in enumerate(dataset.rows, start=1):
        for name, rule in contract.columns.items():
            if name not in dataset_columns:
                continue  # already reported as missing column
            raw = row.get(name)
            if _is_missing(raw, contract.missing_values):
                check("nullable", name)
                if not rule.nullable:
                    agg.add(
                        "nullable",
                        name,
                        f"Column '{name}': 1 value(s) are missing but the column is not nullable.",
                        row=row_idx,
                    )
                continue
            assert raw is not None
            value = raw

            check("type", name)
            ok, parsed = coerce(value, rule.type)
            if not ok:
                agg.add(
                    "type",
                    name,
                    f"Column '{name}': 1 value(s) failed the type check (expected {rule.type}).",
                    row=row_idx,
                )
                continue  # value-level rules need a valid typed value

            if rule.unique:
                check("unique", name)
                seen = seen_unique[name]
                if value in seen:
                    agg.add(
                        "unique",
                        name,
                        f"Column '{name}': 1 duplicate value(s) violate the unique constraint.",
                        row=row_idx,
                    )
                else:
                    seen[value] = row_idx

            if rule.regex is not None:
                check("regex", name)
                if not re.search(rule.regex, value):
                    agg.add(
                        "regex",
                        name,
                        f"Column '{name}': 1 value(s) do not match the required pattern.",
                        row=row_idx,
                    )

            if rule.allowed_values is not None:
                check("allowed_values", name)
                if value not in missing_sets[name] and value not in rule.allowed_values:
                    agg.add(
                        "allowed_values",
                        name,
                        f"Column '{name}': 1 value(s) are not in the allowed value list.",
                        row=row_idx,
                    )

            if rule.min is not None:
                check("min", name)
                if parsed < rule.min:
                    agg.add(
                        "min",
                        name,
                        f"Column '{name}': 1 value(s) are below the minimum of {rule.min:g}.",
                        row=row_idx,
                    )
            if rule.max is not None:
                check("max", name)
                if parsed > rule.max:
                    agg.add(
                        "max",
                        name,
                        f"Column '{name}': 1 value(s) exceed the maximum of {rule.max:g}.",
                        row=row_idx,
                    )

            if rule.min_length is not None:
                check("min_length", name)
                if len(value) < rule.min_length:
                    agg.add(
                        "min_length",
                        name,
                        f"Column '{name}': 1 value(s) are shorter than min_length "
                        f"{rule.min_length}.",
                        row=row_idx,
                    )
            if rule.max_length is not None:
                check("max_length", name)
                if len(value) > rule.max_length:
                    agg.add(
                        "max_length",
                        name,
                        f"Column '{name}': 1 value(s) exceed max_length {rule.max_length}.",
                        row=row_idx,
                    )

    failing = agg.failing_keys()
    checks_passed = sum(1 for key in checks if key not in failing)
    checks_failed = sum(1 for key in checks if key in failing)

    column_summaries: dict[str, dict[str, Any]] = {}
    for name in contract.columns:
        col_checks = [k for k in checks if k[1] == name]
        failed_rules = sorted({k[0] for k in col_checks if k in failing})
        violation_count = sum(v.count for v in agg.violations() if v.column == name)
        column_summaries[name] = {
            "rules_checked": len(col_checks),
            "rules_failed": failed_rules,
            "violation_count": violation_count,
        }

    violations = agg.violations()
    return ValidationReport(
        dataset=dataset.source,
        contract=contract_path or "(contract)",
        row_count=dataset.row_count,
        passed=not any(v.severity == "error" for v in violations),
        violations=violations,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        column_summaries=column_summaries,
    )
