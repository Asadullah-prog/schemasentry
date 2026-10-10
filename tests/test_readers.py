"""Tests for dataset readers: CSV, Excel, JSON, JSON Lines."""

import json

import pytest
from openpyxl import Workbook

from schemasentry.readers import DatasetError, read_dataset


def write(path, text, encoding="utf-8"):
    path.write_text(text, encoding=encoding)
    return str(path)


def test_csv_basic(tmp_path):
    p = write(tmp_path / "d.csv", "a,b\n1,2\n3,4\n")
    ds = read_dataset(p)
    assert ds.columns == ["a", "b"]
    assert ds.row_count == 2
    assert ds.rows[0] == {"a": "1", "b": "2"}


def test_csv_quoted_commas_and_unicode(tmp_path):
    p = write(tmp_path / "d.csv", 'name,note\n"Doe, Jane","héllo, wörld"\n')
    ds = read_dataset(p)
    assert ds.rows[0] == {"name": "Doe, Jane", "note": "héllo, wörld"}


def test_csv_bom(tmp_path):
    raw = "a,b\n1,2\n".encode("utf-8-sig")
    p = tmp_path / "d.csv"
    p.write_bytes(raw)
    ds = read_dataset(str(p))
    assert ds.columns == ["a", "b"]


def test_csv_empty_file(tmp_path):
    p = write(tmp_path / "d.csv", "")
    with pytest.raises(DatasetError, match="empty"):
        read_dataset(p)


def test_csv_missing_file(tmp_path):
    with pytest.raises(DatasetError, match="not found"):
        read_dataset(str(tmp_path / "nope.csv"))


def test_csv_duplicate_headers(tmp_path):
    p = write(tmp_path / "d.csv", "a,a\n1,2\n")
    with pytest.raises(DatasetError, match="duplicate"):
        read_dataset(p)


def test_csv_blank_header(tmp_path):
    p = write(tmp_path / "d.csv", "a,\n1,2\n")
    with pytest.raises(DatasetError, match="blank"):
        read_dataset(p)


def test_csv_extra_fields_error(tmp_path):
    p = write(tmp_path / "d.csv", "a,b\n1,2,3\n")
    with pytest.raises(DatasetError, match="more fields"):
        read_dataset(p)


def test_csv_unsupported_format(tmp_path):
    p = write(tmp_path / "d.tsv", "a\tb\n")
    with pytest.raises(DatasetError, match="unsupported format"):
        read_dataset(p)


def test_csv_format_override(tmp_path):
    p = write(tmp_path / "d.txt", "a,b\n1,2\n")
    ds = read_dataset(p, format="csv")
    assert ds.row_count == 1


def test_sheet_on_csv_rejected(tmp_path):
    p = write(tmp_path / "d.csv", "a\n1\n")
    with pytest.raises(DatasetError, match="--sheet"):
        read_dataset(p, sheet="x")


def _workbook(tmp_path, sheets):
    p = tmp_path / "d.xlsx"
    wb = Workbook()
    first = True
    for name, rows in sheets.items():
        ws = wb.active if first else wb.create_sheet(name)
        ws.title = name
        for row in rows:
            ws.append(row)
        first = False
    wb.save(p)
    return str(p)


def test_xlsx_default_sheet(tmp_path):
    p = _workbook(tmp_path, {"data": [["a", "b"], [1, 2]], "other": [["z"], [9]]})
    ds = read_dataset(p)
    assert ds.sheet == "data"
    assert ds.rows[0] == {"a": "1", "b": "2"}


def test_xlsx_named_sheet(tmp_path):
    p = _workbook(tmp_path, {"data": [["a"], [1]], "other": [["z"], [9]]})
    ds = read_dataset(p, sheet="other")
    assert ds.sheet == "other"
    assert ds.columns == ["z"]


def test_xlsx_missing_sheet(tmp_path):
    p = _workbook(tmp_path, {"data": [["a"], [1]]})
    with pytest.raises(DatasetError, match="not found"):
        read_dataset(p, sheet="nope")


def test_xlsx_empty_sheet(tmp_path):
    p = _workbook(tmp_path, {"empty": []})
    with pytest.raises(DatasetError, match="empty"):
        read_dataset(p, sheet="empty")


def test_json_array(tmp_path):
    p = write(tmp_path / "d.json", json.dumps([{"a": 1, "b": "x"}, {"a": 2}]))
    ds = read_dataset(p)
    assert ds.columns == ["a", "b"]
    assert ds.rows[1] == {"a": "2", "b": None}


def test_json_lines(tmp_path):
    p = write(tmp_path / "d.jsonl", '{"a": 1}\n{"a": 2}\n')
    ds = read_dataset(p)
    assert ds.format == "jsonl"
    assert ds.row_count == 2


def test_json_not_array_of_objects(tmp_path):
    p = write(tmp_path / "d.json", '{"a": 1}')
    with pytest.raises(DatasetError, match="array of objects"):
        read_dataset(p)


def test_json_malformed(tmp_path):
    p = write(tmp_path / "d.json", '{"a": ')
    with pytest.raises(DatasetError):
        read_dataset(p)


def test_json_empty(tmp_path):
    p = write(tmp_path / "d.json", "[]")
    with pytest.raises(DatasetError, match="no records"):
        read_dataset(p)
