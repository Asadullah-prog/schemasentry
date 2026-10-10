# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a vulnerability

**Do not open a public issue for security reports.**

Email the maintainers with a description of the issue, steps to reproduce,
and the version affected. You can expect an acknowledgement within 7 days.
We will work with you on a fix and credit you in the release notes unless
you prefer to remain anonymous.

## Security design

SchemaSentry is built to handle untrusted input safely:

- **Local-only.** Validation performs no network requests. Datasets never
  leave the machine (or the CI runner).
- **No code execution.** YAML contracts are parsed with `yaml.safe_load`;
  regexes come from the contract author and are matched, never evaluated as
  code. Dataset contents are treated as plain strings.
- **No secret leakage.** Reports, logs, and GitHub job summaries contain
  rule names, column names, counts, and row numbers — never raw cell values.
  There is intentionally no "show sample values" mode in v1.
- **Safe file handling.** Readers use UTF-8 with BOM tolerance, bounded
  error messages, and explicit errors for ambiguous inputs instead of
  silent guessing.

## Limitations to be aware of

- Contracts are trusted configuration: a malicious contract could exfiltrate
  data only if the *runner* is compromised — review contracts like code.
- Very large files are read into memory (see README limitations); a hostile
  multi-GB file could exhaust memory on the validating machine.
- Regexes are author-controlled; catastrophic backtracking in a hand-written
  pattern is the contract author's responsibility.
