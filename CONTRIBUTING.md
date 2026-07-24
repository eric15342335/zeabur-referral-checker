# Contributing

## Setup

```bash
uv sync --all-groups
uv run pre-commit install
```

## Workflow

1. Create a focused branch.
2. Add or update tests for behavior changes.
3. Run `uv run python scripts/quality.py format`.
4. Run `uv run python scripts/quality.py`.
5. Open a pull request describing the behavior change and its verification.

Keep changes scoped to referral-code validation, its supported interfaces,
installation, deployment, or maintenance. Do not commit credentials, raw HAR
files, real referral codes, generated build output, or local environment files.
