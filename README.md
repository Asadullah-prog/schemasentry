# SchemaSentry

**Know when your data breaks before your application, report, or analytics pipeline breaks.**

SchemaSentry is a privacy-first, local-first data contract validation tool.
Point it at a CSV, Excel, or JSON dataset and a YAML contract; it tells you —
on your laptop or in CI — whether the data still matches the shape you expect.

## 1. The problem

Datasets change silently: a producer renames a column, starts emitting ages as
text, adds unexpected columns, or lets nulls creep into a key field. The
failure surfaces hours later as a broken dashboard, a failed load, or wrong
numbers in a report. SchemaSentry catches the structural change at the source
by validating every dataset against an explicit, versioned contract.

## 2. Who it's for

- **Analysts** running a one-off check before trusting a new export.
- **Data engineers** guarding pipeline inputs with contracts checked into git.
- **Researchers and small teams** who want CI enforcement without standing up
  a data platform, a cloud account, or a paid service.

Typical uses: validating vendor data drops, checking ETL outputs before
publishing, and blocking merges that would ship a malformed dataset.

## 3. Features

- `profile` — observed statistics and conservative type inference for any dataset.
- `init` — generate a documented starter YAML contract from a dataset.
- `check` — validate a dataset against a contract (exit code `1` on violation).
- `report` — structured validation reports with column summaries, in terminal
  or JSON form.
- Column rules: types, nullability, uniqueness, regex, allowed values, numeric
  min/max, string length bounds, row-count bounds, missing-value conventions,
  and strictness for unexpected columns.
- Contracts are self-validating: unknown rules, bad thresholds, and
  contradictory constraints fail fast with actionable errors.
- Reusable GitHub Action that installs from source (no PyPI needed) and writes
  a data-leak-free job summary.
- Local-only: no network calls, no accounts, no telemetry, no raw values in output.

## 4. Supported formats and limitations

| Format | Support |
|---|---|
| CSV | UTF-8 with/without BOM, quoted fields, commas in values, Unicode |
| Excel `.xlsx` | Sheet selection via `--sheet` (defaults to the active sheet) |
| JSON | Array of objects |
| JSON Lines | `.jsonl` / `.ndjson`, one object per line |

**Known limitations (v1):**

- Datasets are read fully into memory; multi-GB files may exhaust memory.
  Streaming validation is on the roadmap.
- Type checks treat every cell as a string: `integer` means "parses as an
  integer". This is deliberate and documented, keeping CSV/Excel behavior consistent.
- Type inference in `profile` is a best-effort guess, always labeled as such.
- Ambiguous inputs fail loudly instead of being guessed (duplicate headers,
  blank headers, ragged rows, malformed JSON).

## 5. Installation

Requires Python 3.11+.

```bash
pip install schemasentry        # once published to PyPI
```

Or install from source (this is also what the GitHub Action does):

```bash
git clone <repo-url> && cd schemasentry
pip install .
```

Verify:

```bash
schemasentry --help
```

## 6. Quick demo

```bash
schemasentry profile examples/customers.csv
schemasentry init examples/customers.csv --output my-contract.yml   # review & edit it
schemasentry check examples/customers.csv --contract examples/schemasentry.yml
```

## 7. Sample contract

`examples/schemasentry.yml` (see `docs/contract-reference.md` for the full reference):

```yaml
version: "1"
name: customers

columns:
  customer_id:
    type: string
    required: true
    nullable: false
    unique: true
  email:
    type: string
    required: true
    nullable: false
    regex: "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"
  age:
    type: integer
    required: false
    nullable: true
    min: 0
    max: 120
  status:
    type: string
    required: true
    nullable: false
    allowed_values: ["active", "trial", "churned"]

row_counts:
  min_rows: 1
  max_rows: 100000

strictness:
  extra_columns: error   # or: warn | ignore
```

## 8. Example commands and output

Passing check:

```bash
$ schemasentry check examples/customers.csv --contract examples/schemasentry.yml
```

```text
Validation PASSED — examples/customers.csv
Contract: examples/schemasentry.yml
Rows: 20   Checks passed: 25   Checks failed: 0
All checks passed.
```

Failing check (exit code `1`):

```bash
$ schemasentry check broken.csv --contract examples/schemasentry.yml
```

```text
Validation FAILED — broken.csv
Contract: examples/schemasentry.yml
Rows: 2   Checks passed: 20   Checks failed: 4
```

followed by a violations table naming the rule, column, violation count, and
example row numbers — never the offending values.

Machine-readable output for automation:

```bash
$ schemasentry check examples/customers.csv --contract examples/schemasentry.yml --format json
```

```json
{
  "status": "passed",
  "dataset": "examples/customers.csv",
  "contract": "examples/schemasentry.yml",
  "row_count": 20,
  "checks_passed": 25,
  "checks_failed": 0,
  "violations": [],
  "column_summaries": {
    "customer_id": {
      "rules_checked": 3,
      "rules_failed": [],
      "violation_count": 0
    }
  }
}
```

Exit codes: `0` success · `1` validation failure · `2` operational/configuration error.
See `docs/contract-reference.md` for the rule reference.

## 9. GitHub Actions setup

Use the reusable composite action to validate datasets on every push:

```yaml
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0
      - uses: <owner>/schemasentry@<full-commit-sha>
        with:
          dataset: data/customers.csv
          contract: contracts/customers.yml
```

The action installs SchemaSentry from its own source (no PyPI dependency),
writes a job summary with counts only, and fails the job on contract
violations. A complete adaptable workflow is in
`.github/workflows/example-data-check.yml`; the full guide, including how to
update pinned SHAs, is in `docs/github-actions.md`.

## 10. Privacy and security

- **Local-first.** All processing happens on your machine or runner. No
  network requests are made during validation.
- **No leakage by design.** Reports, logs, and job summaries contain rule
  names, column names, violation counts, and row numbers — never raw cell
  values. There is no "show samples" mode in v1.
- **Untrusted input.** Datasets and contracts are parsed defensively
  (`yaml.safe_load`, strict CSV/JSON parsing); nothing is executed.
- See `SECURITY.md` for the vulnerability reporting process and residual
  limitations.

## 11. Testing and development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -q                        # full test suite
ruff check src/ tests/           # lint
ruff format --check src/ tests/  # format check
python -m build                  # package build
```

Architecture (engine stays independent of the CLI):

```text
src/schemasentry/
├── readers.py     # CSV / XLSX / JSON → Dataset
├── contract.py    # YAML → Contract + self-validation
├── profiler.py    # observed statistics, type inference
├── validator.py   # pure validation engine → ValidationReport
└── cli.py         # Typer commands, Rich output, exit codes
```

## 12. Contributing

See `CONTRIBUTING.md` for the workflow, coding standards, and good first
issues. Bug reports and feature requests use the templates in
`.github/ISSUE_TEMPLATE/`. By contributing you agree to the Apache-2.0 license
terms; this project follows the Contributor Covenant (`CODE_OF_CONDUCT.md`).

## 13. Roadmap

Near term: `date` min/max constraints, violation-rate thresholds, streaming
validation for large files, contract diffing. Longer term: Parquet support,
SARIF output, pre-commit packaging. Explicit non-goals: cloud hosting,
accounts/billing, AI features, web dashboards, uploading datasets anywhere.
Full list in `ROADMAP.md`.

## 14. License

Apache License 2.0 — see `LICENSE`.

---

*Name note: an unrelated single-file GraphQL security-audit script named
`schemasentry` exists on GitHub; this project is a distinct data-contract
validation tool for tabular datasets and makes no claim to be the first of its
kind.*
