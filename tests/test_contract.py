"""Tests for contract loading and self-validation."""

import pytest

from schemasentry.contract import ContractError, load_contract

VALID = """\
version: "1"
name: t
columns:
  id:
    type: string
    required: true
    nullable: false
    unique: true
"""


def write_contract(tmp_path, text):
    p = tmp_path / "c.yml"
    p.write_text(text)
    return str(p)


def test_valid_contract(tmp_path):
    c = load_contract(write_contract(tmp_path, VALID))
    assert c.version == "1"
    assert c.columns["id"].unique is True
    assert c.extra_columns == "warn"  # default


def test_missing_file(tmp_path):
    with pytest.raises(ContractError, match="not found"):
        load_contract(str(tmp_path / "nope.yml"))


def test_empty_file(tmp_path):
    with pytest.raises(ContractError, match="empty"):
        load_contract(write_contract(tmp_path, ""))


def test_invalid_yaml(tmp_path):
    with pytest.raises(ContractError, match="invalid YAML"):
        load_contract(write_contract(tmp_path, "columns: [unclosed"))


def test_missing_version(tmp_path):
    with pytest.raises(ContractError, match="version"):
        load_contract(write_contract(tmp_path, "columns:\n  a:\n    type: string\n"))


def test_wrong_version(tmp_path):
    with pytest.raises(ContractError, match="unsupported contract version"):
        load_contract(write_contract(tmp_path, VALID.replace('"1"', '"99"')))


def test_unknown_rule(tmp_path):
    bad = VALID.replace("unique: true", "uniqueness: true")
    with pytest.raises(ContractError, match="unknown rule"):
        load_contract(write_contract(tmp_path, bad))


def test_unknown_type(tmp_path):
    bad = VALID.replace("type: string", "type: number")
    with pytest.raises(ContractError, match="unknown type"):
        load_contract(write_contract(tmp_path, bad))


def test_bad_regex(tmp_path):
    bad = VALID + '  email:\n    type: string\n    regex: "(["\n'
    with pytest.raises(ContractError, match="invalid regex"):
        load_contract(write_contract(tmp_path, bad))


def test_min_greater_than_max(tmp_path):
    bad = VALID + "  age:\n    type: integer\n    min: 10\n    max: 5\n"
    with pytest.raises(ContractError, match="greater than max"):
        load_contract(write_contract(tmp_path, bad))


def test_min_on_string_column(tmp_path):
    bad = VALID + "  id2:\n    type: string\n    min: 1\n"
    with pytest.raises(ContractError, match="min/max only apply"):
        load_contract(write_contract(tmp_path, bad))


def test_min_length_on_integer(tmp_path):
    bad = VALID + "  n:\n    type: integer\n    min_length: 2\n"
    with pytest.raises(ContractError, match="min_length/max_length only apply"):
        load_contract(write_contract(tmp_path, bad))


def test_empty_allowed_values(tmp_path):
    bad = VALID + "  s:\n    type: string\n    allowed_values: []\n"
    with pytest.raises(ContractError, match="non-empty list"):
        load_contract(write_contract(tmp_path, bad))


def test_bad_extra_columns_mode(tmp_path):
    bad = VALID + "strictness:\n  extra_columns: explode\n"
    with pytest.raises(ContractError, match="extra_columns"):
        load_contract(write_contract(tmp_path, bad))


def test_unknown_top_level_key(tmp_path):
    with pytest.raises(ContractError, match="unknown top-level"):
        load_contract(write_contract(tmp_path, VALID + "frobnicate: 1\n"))


def test_negative_min_rows(tmp_path):
    with pytest.raises(ContractError, match="non-negative integer"):
        load_contract(write_contract(tmp_path, VALID + "row_counts:\n  min_rows: -1\n"))


def test_min_rows_exceeds_max_rows(tmp_path):
    with pytest.raises(ContractError, match="exceeds max_rows"):
        load_contract(
            write_contract(tmp_path, VALID + "row_counts:\n  min_rows: 5\n  max_rows: 2\n")
        )


def test_missing_values_must_be_strings(tmp_path):
    with pytest.raises(ContractError, match="missing_values"):
        load_contract(write_contract(tmp_path, VALID + "missing_values: [1, 2]\n"))
