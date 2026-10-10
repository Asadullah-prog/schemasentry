"""YAML contract loading and self-validation.

A contract describes the expected shape of a dataset. Contracts are
versioned; this module only accepts the current ``CONTRACT_VERSION``.
YAML is parsed with ``yaml.safe_load`` and contracts are validated for
unknown rule names, bad thresholds, and contradictory constraints *before*
any dataset is checked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONTRACT_VERSION = "1"

COLUMN_TYPES = ("string", "integer", "float", "boolean", "date")
EXTRA_COLUMN_MODES = ("error", "warn", "ignore")

# Rule names allowed inside a column definition. Anything else is rejected.
COLUMN_RULES = {
    "type",
    "required",
    "nullable",
    "unique",
    "regex",
    "allowed_values",
    "min",
    "max",
    "min_length",
    "max_length",
    "description",
}


class ContractError(Exception):
    """Raised when a contract file is invalid."""


@dataclass
class ColumnRule:
    name: str
    type: str = "string"
    required: bool = True
    nullable: bool = False
    unique: bool = False
    regex: str | None = None
    allowed_values: list[Any] | None = None
    min: float | None = None
    max: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    description: str | None = None


@dataclass
class Contract:
    version: str = CONTRACT_VERSION
    name: str | None = None
    description: str | None = None
    missing_values: list[str] = field(
        default_factory=lambda: ["NA", "N/A", "null", "NULL", "None", "none"]
    )
    columns: dict[str, ColumnRule] = field(default_factory=dict)
    min_rows: int | None = None
    max_rows: int | None = None
    extra_columns: str = "warn"


def _fail(path: str, message: str) -> ContractError:
    return ContractError(f"{path}: invalid contract: {message}")


def _parse_column(name: str, raw: Any, path: str) -> ColumnRule:
    where = f"column {name!r}"
    if not isinstance(raw, dict):
        raise _fail(path, f"{where}: expected a mapping of rules, got {type(raw).__name__}.")
    unknown = set(raw) - COLUMN_RULES
    if unknown:
        raise _fail(path, f"{where}: unknown rule(s): {', '.join(sorted(unknown))}.")
    rule = ColumnRule(name=name)
    declared_type = raw.get("type", "string")
    if declared_type not in COLUMN_TYPES:
        raise _fail(
            path,
            f"{where}: unknown type {declared_type!r}; expected one of {', '.join(COLUMN_TYPES)}.",
        )
    rule.type = declared_type
    for flag in ("required", "nullable", "unique"):
        value = raw.get(flag, getattr(rule, flag))
        if not isinstance(value, bool):
            raise _fail(path, f"{where}: {flag!r} must be true or false.")
        setattr(rule, flag, value)
    regex = raw.get("regex")
    if regex is not None:
        if not isinstance(regex, str):
            raise _fail(path, f"{where}: regex must be a string.")
        try:
            re.compile(regex)
        except re.error as exc:
            raise _fail(path, f"{where}: invalid regex {regex!r}: {exc}.") from exc
        rule.regex = regex
    allowed = raw.get("allowed_values")
    if allowed is not None:
        if not isinstance(allowed, list) or not allowed:
            raise _fail(path, f"{where}: allowed_values must be a non-empty list.")
        rule.allowed_values = [str(v) for v in allowed]
    for bound in ("min", "max"):
        value = raw.get(bound)
        if value is not None:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise _fail(path, f"{where}: {bound} must be a number.")
            setattr(rule, bound, float(value))
    if rule.min is not None and rule.max is not None and rule.min > rule.max:
        raise _fail(path, f"{where}: min ({rule.min}) is greater than max ({rule.max}).")
    if rule.type not in ("integer", "float") and (rule.min is not None or rule.max is not None):
        raise _fail(path, f"{where}: min/max only apply to integer or float columns.")
    for bound in ("min_length", "max_length"):
        value = raw.get(bound)
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise _fail(path, f"{where}: {bound} must be a non-negative integer.")
            setattr(rule, bound, value)
    if (
        rule.min_length is not None
        and rule.max_length is not None
        and rule.min_length > rule.max_length
    ):
        raise _fail(
            path, f"{where}: min_length ({rule.min_length}) exceeds max_length ({rule.max_length})."
        )
    if rule.type != "string" and (rule.min_length is not None or rule.max_length is not None):
        raise _fail(path, f"{where}: min_length/max_length only apply to string columns.")
    description = raw.get("description")
    if description is not None and not isinstance(description, str):
        raise _fail(path, f"{where}: description must be a string.")
    rule.description = description
    return rule


def load_contract(path: str | Path) -> Contract:
    """Load and validate a YAML contract file."""
    file_path = Path(path)
    src = str(path)
    if not file_path.is_file():
        raise ContractError(f"{src}: contract file not found.")
    try:
        text = file_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ContractError(f"{src}: cannot read contract file: {exc.strerror or exc}") from exc
    except UnicodeDecodeError as exc:
        raise ContractError(f"{src}: contract file is not valid UTF-8 text.") from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ContractError(f"{src}: invalid YAML: {exc}.") from exc
    if raw is None:
        raise ContractError(f"{src}: contract file is empty.")
    if not isinstance(raw, dict):
        raise ContractError(f"{src}: contract must be a mapping at the top level.")

    version = raw.get("version", raw.get("schemasentry_version"))
    if version is None:
        raise _fail(src, "missing required 'version' field.")
    if str(version) != CONTRACT_VERSION:
        raise _fail(
            src,
            f"unsupported contract version {version!r}; this tool supports version {CONTRACT_VERSION!r}.",
        )

    contract = Contract(version=str(version))
    for key in ("name", "description"):
        value = raw.get(key)
        if value is not None and not isinstance(value, str):
            raise _fail(src, f"{key!r} must be a string.")
        setattr(contract, key, value)

    missing_values = raw.get("missing_values", contract.missing_values)
    if not isinstance(missing_values, list) or not all(isinstance(v, str) for v in missing_values):
        raise _fail(src, "missing_values must be a list of strings.")
    contract.missing_values = missing_values

    raw_columns = raw.get("columns")
    if not isinstance(raw_columns, dict) or not raw_columns:
        raise _fail(src, "'columns' must be a non-empty mapping of column rules.")
    for name, rules in raw_columns.items():
        if not isinstance(name, str) or not name.strip():
            raise _fail(src, "column names must be non-empty strings.")
        contract.columns[name] = _parse_column(name, rules, src)

    row_counts = raw.get("row_counts", {})
    if not isinstance(row_counts, dict):
        raise _fail(src, "row_counts must be a mapping.")
    unknown_rc = set(row_counts) - {"min_rows", "max_rows"}
    if unknown_rc:
        raise _fail(src, f"row_counts: unknown key(s): {', '.join(sorted(unknown_rc))}.")
    for key in ("min_rows", "max_rows"):
        value = row_counts.get(key)
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise _fail(src, f"row_counts.{key} must be a non-negative integer.")
            setattr(contract, key, value)
    if (
        contract.min_rows is not None
        and contract.max_rows is not None
        and contract.min_rows > contract.max_rows
    ):
        raise _fail(
            src,
            f"row_counts: min_rows ({contract.min_rows}) exceeds max_rows ({contract.max_rows}).",
        )

    strictness = raw.get("strictness", {})
    if not isinstance(strictness, dict):
        raise _fail(src, "strictness must be a mapping.")
    unknown_s = set(strictness) - {"extra_columns"}
    if unknown_s:
        raise _fail(src, f"strictness: unknown key(s): {', '.join(sorted(unknown_s))}.")
    extra_columns = strictness.get("extra_columns", contract.extra_columns)
    if extra_columns not in EXTRA_COLUMN_MODES:
        raise _fail(
            src,
            f"strictness.extra_columns must be one of {', '.join(EXTRA_COLUMN_MODES)}.",
        )
    contract.extra_columns = extra_columns

    unknown_top = set(raw) - {
        "version",
        "schemasentry_version",
        "name",
        "description",
        "missing_values",
        "columns",
        "row_counts",
        "strictness",
    }
    if unknown_top:
        raise _fail(src, f"unknown top-level key(s): {', '.join(sorted(unknown_top))}.")

    return contract
