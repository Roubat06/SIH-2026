# Sentinel Tool test datasets

All files in this directory are synthetic. They do not represent real Bitcoin transactions, wallets, people, or network peers.

## Comprehensive mixed-traffic dataset

Use `sentineltool-test-dataset.json` for end-to-end testing through **Datasets → Choose a dataset**.

It contains:

- 240 synthetic transactions and 45 synthetic network observations;
- ordinary one-input/two-output traffic for a usable baseline;
- three explicit fan-out transactions with 14–18 outputs;
- two explicit consolidation transactions with 12–14 inputs;
- missing-fee, unusually high-fee, high-value, confirmed, and unconfirmed examples;
- linked outputs for transaction-graph and investigation-timeline testing;
- reserved documentation-only IP ranges for relay observations.

With the current analysis configuration, a clean import produces eight alerts: five high-priority rule alerts and three additional medium-priority model-only alerts. There are three `fan_out`, two `fan_in`, and seven Isolation Forest detections; some transactions trigger both a rule and the model.

The JSON includes `dataset_info` with the exact record numbers and TXIDs expected to trigger the count rules. Sentinel Tool ignores that metadata during import.

Regenerate the file deterministically from the repository root:

```bash
python3 scripts/generate_test_dataset.py
```

The generated file is approximately 270 KB, below the hosted 4 MB upload limit.

## Small format examples

- `transactions.csv` demonstrates CSV ingestion with JSON-encoded input and output cells.
- `transactions.xml` demonstrates the minimal XML structure.
- `synthetic-training.json` is the original branching training scenario.
