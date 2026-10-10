# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.1.0] - 2026-10-10

### Added
- Initial release of SchemaSentry.
- CLI commands: `profile`, `init`, `check`, `report` with terminal and JSON output.
- Dataset readers for CSV (BOM/Unicode/quoting aware), Excel (.xlsx with sheet
  selection), JSON arrays, and JSON Lines.
- Versioned YAML contract format with column rules: types, nullability,
  uniqueness, regex, allowed values, numeric min/max, string length bounds,
  row-count bounds, missing-value conventions, and extra-column strictness.
- Contract self-validation with actionable errors (unknown rules, bad
  thresholds, contradictory constraints).
- Composite GitHub Action (`action.yml`) with job summaries, distinct exit
  codes, and no dataset-content leakage; example workflow included.
- Documentation: contract reference, GitHub Actions guide, README, contributing
  guide, security policy, roadmap.
- Test suite: 84 tests covering readers, contracts, validation rules, CLI exit
  codes, JSON output, and privacy (no sample-value leakage).
