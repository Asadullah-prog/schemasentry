# Contract reference

SchemaSentry contracts are YAML files describing the expected shape of a
dataset. The contract format is versioned; the current version is `"1"`.

## Full example

```yaml
version: "1"
name: customers
description: "Customer export from the CRM."

# Tokens treated as missing values, in addition to empty cells.
missing_values: ["NA", "N/A", "null", "NULL", "None", "none"]

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
  extra_columns: warn   # error | warn | ignore
```

## Top-level fields

| Field | Required | Description |
|---|---|---|
| `version` | yes | Contract format version. Must be `"1"`. |
| `name` | no | Human-readable dataset name. |
| `description` | no | Free-text description. |
| `missing_values` | no | Extra string tokens treated as missing (empty cells always count as missing). |
| `columns` | yes | Non-empty mapping of column name → rules. |
| `row_counts` | no | `min_rows` / `max_rows` (non-negative integers). |
| `strictness` | no | `extra_columns`: `error` (default behavior if omitted is `warn`), `warn`, or `ignore`. |

## Column rules

| Rule | Applies to | Description |
|---|---|---|
| `type` | all | One of `string`, `integer`, `float`, `boolean`, `date`. Values arrive as strings (CSV/Excel), so `integer` means "parses as an integer". `boolean` accepts `true/false/1/0/yes/no` (case-insensitive). `date` accepts ISO 8601 (`YYYY-MM-DD`). |
| `required` | all | Default `true`. If `false`, the column may be absent without failing. |
| `nullable` | all | Default `false`. Whether missing values are allowed. |
| `unique` | all | Default `false`. Every non-missing value must be distinct. |
| `regex` | `string` | Python regular expression the value must match (`re.search` semantics). |
| `allowed_values` | all | Non-empty list of permitted string values. |
| `min` / `max` | `integer`, `float` | Inclusive numeric bounds. |
| `min_length` / `max_length` | `string` | Inclusive string length bounds. |
| `description` | all | Free-text note for readers of the contract. |

## Contract self-validation

`schemasentry check` validates the contract *before* touching the dataset and
fails with exit code 2 (configuration error) on:

- missing or unsupported `version`
- unknown rule names or unknown top-level keys
- unknown column `type`
- invalid `regex`
- `min` greater than `max`, or `min_length` greater than `max_length`
- `min`/`max` on non-numeric columns; `min_length`/`max_length` on non-string columns
- empty `allowed_values`
- negative `min_rows`/`max_rows`, or `min_rows` greater than `max_rows`
- invalid `strictness.extra_columns` value

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (or validation passed). |
| `1` | Validation failure: the dataset violates the contract. |
| `2` | Operational/configuration error: unreadable file, invalid contract, bad CLI usage. |

## Generating a starter contract

`schemasentry init dataset.csv --output schemasentry.yml` writes a documented
starter contract. Inferred rules are marked `INFERRED`; risky constraints
(`unique`, `min`/`max`, `regex`, `allowed_values`) are left commented out for
you to enable deliberately after review.
