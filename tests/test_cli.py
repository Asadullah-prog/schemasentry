"""Tests for the profiler and the Typer CLI (exit codes, JSON, privacy)."""

import json

from typer.testing import CliRunner

from schemasentry.cli import app
from schemasentry.profiler import profile
from schemasentry.readers import read_dataset

runner = CliRunner()


def write_csv(path, text):
    path.write_text(text)
    return str(path)


def write_contract(path, text):
    path.write_text(text)
    return str(path)


GOOD_CSV = "id,age\n1,30\n2,25\n"
GOOD_CONTRACT = """\
version: "1"
columns:
  id:
    type: integer
    required: true
    nullable: false
    unique: true
  age:
    type: integer
    required: true
    nullable: false
    min: 0
    max: 120
"""


def test_profiler_stats(tmp_path):
    p = write_csv(tmp_path / "d.csv", "a,b\n1,x\n2,x\n2,x\n")
    prof = profile(read_dataset(p))
    assert prof["row_count"] == 3
    assert prof["duplicate_rows"] == 1
    col_a = next(c for c in prof["columns"] if c["name"] == "a")
    assert col_a["inferred_type"] == "integer"
    assert col_a["min"] == 1 and col_a["max"] == 2
    assert col_a["distinct_count"] == 2
    # JSON-serializable
    json.dumps(prof)


def test_cli_profile_terminal(tmp_path):
    p = write_csv(tmp_path / "d.csv", GOOD_CSV)
    result = runner.invoke(app, ["profile", p])
    assert result.exit_code == 0
    assert "Rows:" in result.output


def test_cli_profile_json(tmp_path):
    p = write_csv(tmp_path / "d.csv", GOOD_CSV)
    result = runner.invoke(app, ["profile", p, "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["row_count"] == 2


def test_cli_init_generates_valid_contract(tmp_path):
    p = write_csv(tmp_path / "d.csv", GOOD_CSV)
    out = str(tmp_path / "gen.yml")
    result = runner.invoke(app, ["init", p, "--output", out])
    assert result.exit_code == 0
    # The generated contract validates the source dataset.
    check = runner.invoke(app, ["check", p, "--contract", out])
    assert check.exit_code == 0
    # Refusing to overwrite without --force.
    again = runner.invoke(app, ["init", p, "--output", out])
    assert again.exit_code == 2


def test_cli_check_pass_exit_0(tmp_path):
    p = write_csv(tmp_path / "d.csv", GOOD_CSV)
    c = write_contract(tmp_path / "c.yml", GOOD_CONTRACT)
    result = runner.invoke(app, ["check", p, "--contract", c])
    assert result.exit_code == 0
    assert "PASSED" in result.output


def test_cli_check_fail_exit_1(tmp_path):
    p = write_csv(tmp_path / "d.csv", "id,age\n1,999\n1,30\n")
    c = write_contract(tmp_path / "c.yml", GOOD_CONTRACT)
    result = runner.invoke(app, ["check", p, "--contract", c])
    assert result.exit_code == 1
    assert "FAILED" in result.output


def test_cli_check_json_no_leak(tmp_path):
    secret = "not-an-email-secret-value"
    p = write_csv(tmp_path / "d.csv", f"id,age\n{secret},30\n")
    c = write_contract(tmp_path / "c.yml", GOOD_CONTRACT)
    result = runner.invoke(app, ["check", p, "--contract", c, "--format", "json"])
    assert result.exit_code == 1
    assert secret not in result.output
    payload = json.loads(result.output)
    assert payload["status"] == "failed"


def test_cli_check_missing_dataset_exit_2(tmp_path):
    c = write_contract(tmp_path / "c.yml", GOOD_CONTRACT)
    result = runner.invoke(app, ["check", "nope.csv", "--contract", c])
    assert result.exit_code == 2


def test_cli_check_bad_contract_exit_2(tmp_path):
    p = write_csv(tmp_path / "d.csv", GOOD_CSV)
    c = write_contract(tmp_path / "c.yml", 'version: "1"\ncolumns: {}\n')
    result = runner.invoke(app, ["check", p, "--contract", c])
    assert result.exit_code == 2


def test_cli_report_json_file(tmp_path):
    p = write_csv(tmp_path / "d.csv", GOOD_CSV)
    c = write_contract(tmp_path / "c.yml", GOOD_CONTRACT)
    out = str(tmp_path / "report.json")
    result = runner.invoke(app, ["report", p, "--contract", c, "--format", "json", "--output", out])
    assert result.exit_code == 0
    payload = json.loads((tmp_path / "report.json").read_text())
    assert payload["status"] == "passed"
    assert payload["tool"].startswith("schemasentry ")


def test_cli_report_fails_exit_1(tmp_path):
    p = write_csv(tmp_path / "d.csv", "id,age\n1,999\n")
    c = write_contract(tmp_path / "c.yml", GOOD_CONTRACT)
    result = runner.invoke(app, ["report", p, "--contract", c])
    assert result.exit_code == 1
    assert "Column summaries" in result.output
