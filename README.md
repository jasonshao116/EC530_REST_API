# EC530_REST_API
We are building a Rest API on drug shortage 

## Python openFDA Drug Shortage Tracker

This project includes a Python tracker that fetches drug shortage records from openFDA and compares them against a local snapshot file.

### Run tracker

From `EC530_REST_API/`:

```bash
python -m srcs.openfda_shortage_tracker
```

First run creates `data/shortage_snapshot.json`.
Later runs show:

- Added shortage records
- Removed shortage records
- Changed records (for example status updates)

### Optional filters

```bash
python -m srcs.openfda_shortage_tracker --search "drug_name:insulin" --limit 50
```

### Useful options

- `--snapshot <path>` use a custom snapshot file
- `--no-save` fetch and diff without writing a snapshot
- `--base-url <url>` override endpoint URL

### Run tests

```bash
pytest -q
```
