# SchemaSentry — Implementation Plan

## Naming check (2026-10-10)
- No PyPI package named `schemasentry` exists (verified via web search; related
  names like `schema`, `schemaxpy`, `schema-enforcer` are different tools).
- One unrelated GitHub repo (`futehc/schemasentry`) is a single-file GraphQL
  security-audit script — different domain, not a published package. Not a
  material collision. We keep the name **SchemaSentry** and will not claim to
  be "the first" tool of this kind. This note is recorded in the README.

## Intended users
Individual analysts/data engineers validating CSV/Excel/JSON datasets locally,
and teams enforcing data contracts in CI (GitHub Actions).

## Key differences vs existing tools
- Local-first, zero-dependency runtime (no cloud, no AI, no accounts).
- YAML contracts are human-editable, versioned, and self-validating.
- First-class GitHub Action that works from the checked-out action source
  (no unpublished-PyPI dependency).
- Deterministic, redaction-safe JSON output for automation.

## Architecture
- `src/schemasentry/readers.py` — CSV/XLSX/JSON → `Dataset` (columns + row dicts).
- `src/schemasentry/contract.py` — YAML → `Contract` dataclasses; contract self-validation.
- `src/schemasentry/profiler.py` — statistics → profile dict (JSON-serializable).
- `src/schemasentry/validator.py` — engine: `validate(dataset, contract) -> ValidationReport`.
  No CLI/Rich imports; pure typed functions.
- `src/schemasentry/cli.py` — Typer app (`profile`, `init`, `check`, `report`).
- Exit codes: `0` success · `1` validation failure · `2` operational/config error.

## Acceptance criteria
1. All four CLI commands work and are exercised against `examples/`.
2. Every validation rule has passing unit tests; invalid inputs produce
   actionable errors and exit code 2.
3. `check` on a violating dataset exits 1 with redaction-safe JSON via `--format json`.
4. `pytest` green, `ruff check` + `ruff format --check` clean, `python -m build` succeeds.
5. `action.yml` composite action + example workflow present; workflow pins
   third-party actions to full commit SHAs (verify SHAs before finalizing).
6. README covers all 14 required sections with zero fabricated claims.

## Not in v1
Cloud hosting, accounts/billing, AI features, web dashboard, sample-value
leakage in reports, streaming validation of multi-GB files (documented limit).
