"""SchemaSentry: privacy-first, local-first data contract validation."""

from schemasentry.contract import Contract, ContractError, load_contract
from schemasentry.readers import Dataset, DatasetError, read_dataset
from schemasentry.validator import ValidationReport, Violation, validate

__version__ = "0.1.0"
__all__ = [
    "Contract",
    "ContractError",
    "Dataset",
    "DatasetError",
    "ValidationReport",
    "Violation",
    "__version__",
    "load_contract",
    "read_dataset",
    "validate",
]
