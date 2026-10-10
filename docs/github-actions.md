# GitHub Actions guide

SchemaSentry ships a reusable **composite action** (`action.yml`) so teams can
enforce data contracts in CI without publishing anything to PyPI.

## How it works

The action:

1. Sets up Python.
2. Installs SchemaSentry **from the checked-out action source**
   (`pip install "$GITHUB_ACTION_PATH"`) — no PyPI package needed.
3. Runs `schemasentry check` with `--format json`, writing the machine-readable
   report to a file.
4. Writes a **job summary** containing only rule names, column names, counts,
   and row numbers — never cell values.
5. Exits with the validator's exit code: `1` for contract violations, `2` for
   configuration/execution errors.

## Usage

```yaml
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0
      - uses: <owner>/schemasentry@<full-commit-sha> # e.g. the v0.1.0 tag's commit
        with:
          dataset: data/customers.csv
          contract: contracts/customers.yml
```

A complete adaptable example lives in
`.github/workflows/example-data-check.yml`.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `dataset` | yes | — | Dataset path, relative to `working-directory`. |
| `contract` | yes | — | Contract path, relative to `working-directory`. |
| `sheet` | no | `""` | Excel worksheet name (`.xlsx` only). |
| `input-format` | no | `""` | Override format detection: `csv`, `xlsx`, `json`, `jsonl`. |
| `output-format` | no | `json` | Report format: `json` or `terminal`. |
| `working-directory` | no | `.` | Directory containing dataset and contract. |
| `python-version` | no | `3.12` | Python version for the run. |

## Outputs

| Output | Description |
|---|---|
| `outcome` | `passed`, `failed`, or `error`. |
| `report-path` | Path of the written validation report. |

Example of branching on the outcome:

```yaml
- uses: <owner>/schemasentry@<sha>
  id: data
  with:
    dataset: data/customers.csv
    contract: contracts/customers.yml
- if: steps.data.outputs.outcome == 'failed'
  run: echo "Contract violated — see the job summary."
```

## Security notes

- The action never prints dataset contents. Summaries aggregate violations by
  rule/column with counts and row numbers only.
- Pin the action itself to a full commit SHA in consuming workflows, the same
  way this repository pins `actions/checkout` and `actions/setup-python`.
- The action is **not** published on the GitHub Marketplace; reference it by
  commit SHA from source.

## Updating pinned SHAs

Third-party actions in this repo are pinned to full commit SHAs with the
release tag in a trailing comment (e.g. `actions/checkout@<sha> # v4.4.0`).
To update:

1. Resolve the new tag to its commit:
   `gh api repos/actions/checkout/commits/v4 --jq .sha`
2. Update the SHA **and** the version comment together.
3. Dependabot is configured for the `github-actions` ecosystem and will
   propose these updates weekly.
