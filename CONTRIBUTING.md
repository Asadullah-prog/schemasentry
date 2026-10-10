# Contributing to SchemaSentry

Thanks for considering a contribution. This project aims to stay small,
readable, and trustworthy — please keep that spirit in your changes.

## Getting started

```bash
git clone <repo-url> && cd schemasentry
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Development workflow

1. Create a branch from `main`.
2. Make focused changes: small modules, typed public functions, no new
   dependencies unless clearly justified.
3. Add or update tests under `tests/`. Use synthetic data only — never
   commit real personal or customer data, even in examples.
4. Run the quality gates:

```bash
pytest -q
ruff check src/ tests/
ruff format --check src/ tests/
python -m build
```

5. Update `CHANGELOG.md` (under `Unreleased`) and any affected docs.
6. Open a pull request using the provided template.

## Coding standards

- Python 3.11+ compatible code; run `ruff` clean (config in `pyproject.toml`).
- The validation engine (`validator.py`) must stay independent of the CLI:
  no Typer/Rich imports there.
- Error messages must be actionable and must never include raw cell values.
- Keep `src/` modules small and single-purpose; avoid duplicated validation logic.
- Public functions should be typed.

## Reporting issues

Use the bug report or feature request templates in `.github/ISSUE_TEMPLATE/`.
For security issues, see `SECURITY.md` — do not open a public issue.

## Good first contributions

- Additional reader edge-case tests (encodings, malformed inputs).
- New column rules with tests and contract-reference docs (e.g. `date` min/max).
- Better terminal output for large violation lists (truncation with counts).
- Example contracts for common domains (e-commerce orders, survey exports).
- Performance notes: benchmark profiling on wide CSVs and document limits.

## License

By contributing, you agree that your contributions are licensed under the
Apache License 2.0, the same license as the project.
