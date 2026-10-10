# Roadmap

This is a living list of realistic improvements, roughly ordered. Items move
into `CHANGELOG.md` as they ship. No timelines are promised.

## Near term (0.2.x)

- `date`/`datetime` min/max constraints.
- Row-level rule thresholds (e.g. fail only if more than N% of rows violate).
- Truncated terminal output for very large violation lists (counts preserved).
- `--show-sql` style export: render a contract as a SQL `CREATE TABLE` sketch
  for documentation purposes.
- Performance: stream rows for `check` so multi-GB CSVs use bounded memory;
  document measured limits.

## Medium term (0.3.x)

- Contract `extends` / composition (shared base contracts per team).
- Diff mode: compare two dataset profiles to highlight drift.
- Parquet reader (optional dependency, clearly documented).
- JSON Schema export of a contract for non-Python consumers.

## Longer term / ideas

- Watch mode: re-validate on file change for local iteration.
- SARIF output for code-scanning-style integrations.
- Pre-commit hook packaging.

## Non-goals (will not build)

- Cloud hosting, user accounts, billing.
- AI assistants or chatbots inside the tool.
- A web dashboard.
- Uploading datasets anywhere: local-first is the point.

Have another idea? Open a feature request — the issue template asks about
privacy implications, which helps keep the scope honest.
