"""Tests for the validation engine: every rule, privacy, determinism."""

import pytest

from schemasentry.contract import ColumnRule, Contract
from schemasentry.readers import Dataset
from schemasentry.validator import coerce, validate


def make_dataset(columns, rows):
    return Dataset(columns=columns, rows=rows, source="test.csv", format="csv")


def make_contract(columns, **kwargs):
    kwargs.setdefault("missing_values", [])
    kwargs.setdefault("extra_columns", "ignore")
    return Contract(columns=columns, **kwargs)


def col(name, **kwargs):
    return ColumnRule(name=name, **kwargs)


def passing_report(dataset, contract):
    report = validate(dataset, contract)
    assert report.passed, [v.message for v in report.errors]
    return report


def test_required_column_present():
    ds = make_dataset(["a"], [{"a": "1"}])
    passing_report(ds, make_contract({"a": col("a", required=True)}))


def test_missing_required_column():
    ds = make_dataset(["b"], [{"b": "1"}])
    report = validate(ds, make_contract({"a": col("a", required=True)}))
    assert not report.passed
    assert any(v.rule == "column_present" and v.column == "a" for v in report.errors)


def test_optional_missing_column_ok():
    ds = make_dataset(["b"], [{"b": "1"}])
    passing_report(ds, make_contract({"a": col("a", required=False)}))


@pytest.mark.parametrize("mode", ["error", "warn", "ignore"])
def test_extra_column_modes(mode):
    ds = make_dataset(["a", "b"], [{"a": "1", "b": "2"}])
    contract = make_contract({"a": col("a")}, extra_columns=mode)
    report = validate(ds, contract)
    extra = [v for v in report.violations if v.rule == "extra_column"]
    if mode == "error":
        assert not report.passed and len(extra) == 1 and extra[0].severity == "error"
    elif mode == "warn":
        assert report.passed and len(extra) == 1 and extra[0].severity == "warning"
    else:
        assert report.passed and not extra


@pytest.mark.parametrize(
    "value, declared, expected",
    [
        ("42", "integer", True),
        ("-7", "integer", True),
        ("4.2", "integer", False),
        ("abc", "integer", False),
        ("4.2", "float", True),
        ("42", "float", True),
        ("nanx", "float", False),
        ("true", "boolean", True),
        ("False", "boolean", True),
        ("yes", "boolean", True),
        ("0", "boolean", True),
        ("maybe", "boolean", False),
        ("2023-01-31", "date", True),
        ("31/01/2023", "date", False),
        ("anything", "string", True),
    ],
)
def test_type_coercion(value, declared, expected):
    assert coerce(value, declared)[0] is expected


def test_type_violation():
    ds = make_dataset(["age"], [{"age": "not-a-number"}])
    report = validate(ds, make_contract({"age": col("age", type="integer")}))
    assert not report.passed
    assert any(v.rule == "type" and v.example_rows == [1] for v in report.errors)


def test_nullable():
    ds = make_dataset(["a"], [{"a": None}, {"a": "x"}])
    passing_report(ds, make_contract({"a": col("a", nullable=True)}))
    report = validate(ds, make_contract({"a": col("a", nullable=False)}))
    assert not report.passed
    assert any(v.rule == "nullable" and v.count == 1 for v in report.errors)


def test_missing_value_conventions():
    ds = make_dataset(["a"], [{"a": "NA"}, {"a": "x"}])
    contract = make_contract({"a": col("a", nullable=True)}, missing_values=["NA"])
    passing_report(ds, contract)
    contract2 = make_contract({"a": col("a", nullable=False)}, missing_values=["NA"])
    report = validate(ds, contract2)
    assert not report.passed  # "NA" counts as missing -> nullable violation


def test_unique():
    ds = make_dataset(["id"], [{"id": "1"}, {"id": "1"}, {"id": "2"}])
    report = validate(ds, make_contract({"id": col("id", unique=True)}))
    assert not report.passed
    unique_v = [v for v in report.errors if v.rule == "unique"]
    assert len(unique_v) == 1 and unique_v[0].count == 1 and unique_v[0].example_rows == [2]


def test_regex():
    ds = make_dataset(["email"], [{"email": "good@example.com"}, {"email": "bad"}])
    contract = make_contract({"email": col("email", regex=r"^[^@\s]+@[^@\s]+$")})
    report = validate(ds, contract)
    assert not report.passed
    assert any(v.rule == "regex" and v.example_rows == [2] for v in report.errors)


def test_allowed_values():
    ds = make_dataset(["s"], [{"s": "a"}, {"s": "zzz"}])
    report = validate(ds, make_contract({"s": col("s", allowed_values=["a", "b"])}))
    assert not report.passed
    assert any(v.rule == "allowed_values" for v in report.errors)


def test_min_max():
    ds = make_dataset(["n"], [{"n": "5"}, {"n": "500"}])
    report = validate(ds, make_contract({"n": col("n", type="integer", min=0, max=100)}))
    assert not report.passed
    rules = {v.rule for v in report.errors}
    assert rules == {"max"}


def test_min_max_boundaries_pass():
    ds = make_dataset(["n"], [{"n": "0"}, {"n": "100"}])
    passing_report(ds, make_contract({"n": col("n", type="integer", min=0, max=100)}))


def test_length_rules():
    ds = make_dataset(["s"], [{"s": "toolongvalue"}])
    report = validate(ds, make_contract({"s": col("s", min_length=1, max_length=5)}))
    assert not report.passed
    assert any(v.rule == "max_length" for v in report.errors)


def test_row_counts():
    ds = make_dataset(["a"], [{"a": "1"}])
    report = validate(ds, make_contract({"a": col("a")}, min_rows=2))
    assert not report.passed and any(v.rule == "min_rows" for v in report.errors)
    report = validate(ds, make_contract({"a": col("a")}, max_rows=0))
    assert not report.passed and any(v.rule == "max_rows" for v in report.errors)
    passing_report(ds, make_contract({"a": col("a")}, min_rows=1, max_rows=10))


def test_no_sample_values_leak():
    secret = "S3CR3T-VALUE-12345"
    ds = make_dataset(["email"], [{"email": secret}])
    contract = make_contract({"email": col("email", regex=r"^[^@\s]+@[^@\s]+$")})
    report = validate(ds, contract)
    payload = str(report.to_dict())
    assert secret not in payload
    for v in report.violations:
        assert secret not in v.message


def test_deterministic_output():
    ds = make_dataset(
        ["a", "b"],
        [{"a": "x", "b": "1"}, {"a": "x", "b": "nope"}, {"a": None, "b": "3"}],
    )
    contract = make_contract(
        {
            "a": col("a", nullable=False),
            "b": col("b", type="integer"),
            "c": col("c", required=True),
        },
        extra_columns="ignore",
    )
    first = validate(ds, contract).to_dict()
    second = validate(ds, contract).to_dict()
    assert first == second


def test_column_summaries():
    ds = make_dataset(["a"], [{"a": "bad"}])
    report = validate(ds, make_contract({"a": col("a", type="integer")}))
    summary = report.column_summaries["a"]
    assert summary["rules_checked"] >= 1
    assert "type" in summary["rules_failed"]
    assert summary["violation_count"] >= 1


def test_checks_counted():
    ds = make_dataset(["a"], [{"a": "1"}])
    report = validate(ds, make_contract({"a": col("a", type="integer", unique=True)}))
    assert report.passed
    assert report.checks_passed > 0 and report.checks_failed == 0
