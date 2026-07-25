# Zeabur Referral Checker

Asynchronous referral-code validation through [Zeabur](https://zeabur.com/)'s
[GraphQL](https://graphql.org/) endpoint. The project provides a
[Python](https://www.python.org/) API, a
[Rich](https://github.com/Textualize/rich) CLI, a
[Textual](https://github.com/Textualize/textual) terminal interface, and a
[NiceGUI](https://nicegui.io/documentation/) browser/native interface.

## Screenshots

![Graphical interface](./refcheck-gui.png)

## Table of Contents

* [Requirements](#requirements)
* [Install](#install)
* [Run](#run)
* [Python API](#python-api)
* [Configuration](#configuration)
* [Exit codes](#exit-codes)
* [Development](#development)
* [Prompts](#prompts)

## Requirements

- [Python](https://www.python.org/) 3.12 or newer
- [Astral uv](https://docs.astral.sh/uv/)

## Install

```bash
uv sync
```

For development tools:

```bash
uv sync --all-groups
```

## Run

Before running a check, set `REFCHECK_COOKIE` to a non-empty, authorized Cookie
header value in your environment or untracked `.env` file. The value is required;
do not include the `Cookie:` header name. Missing or rejected authentication stops
the run immediately, so refresh the cookie before retrying.

Validate a Python list:

```bash
uv run refcheck check '["CODE1", "CODE2"]'
```

The CLI also accepts comma-separated or line-separated codes:

```bash
uv run refcheck check 'CODE1,CODE2' --concurrency 8 --rate 4
```

Export results:

```bash
uv run refcheck check '["CODE1", "CODE2"]' --output results.json
uv run refcheck check '["CODE1", "CODE2"]' --output results.csv
```

Launch the terminal interface:

```bash
uv run refcheck tui
```

Launch the browser interface:

```bash
uv run refcheck gui
```

Expose the browser interface for container or remote deployment:

```bash
uv run refcheck gui --host 0.0.0.0 --port 8080
```

Use `--native` to request a native window when the platform supports it.

## Python API

```python
import asyncio

from referral_checker import validate_referral_codes


async def main() -> None:
    summary = await validate_referral_codes(["CODE1", "CODE2"])
    for result in summary.results:
        print(result.code, result.status, result.discount_percent, result.reason)


asyncio.run(main())
```

Results preserve normalized input order. Blank entries are removed and
duplicate codes are checked once.

## Configuration

Copy `.env.example` to `.env` or set `REFCHECK_*` environment variables. Fill in
the required `REFCHECK_COOKIE` with the complete Cookie header value, without the
`Cookie:` prefix.

| Variable | Default | Purpose |
|---|---:|---|
| `REFCHECK_ENDPOINT` | `https://api-bunny.zeabur.com/graphql` | GraphQL endpoint |
| `REFCHECK_ORIGIN` | `https://zeabur.com` | Origin and referer headers |
| `REFCHECK_LOCALE` | `en-US` | Zeabur locale header |
| `REFCHECK_ORDER_TYPE` | `RENT_SERVER` | Referral validation order type |
| `REFCHECK_CONCURRENCY` | `8` | Maximum concurrent validations |
| `REFCHECK_REQUESTS_PER_SECOND` | `4` | Request-rate limit |
| `REFCHECK_TIMEOUT_SECONDS` | `15` | Request timeout |
| `REFCHECK_RETRIES` | `3` | Attempts for transient transport failures |
| `REFCHECK_COOKIE` | required | Non-empty authorized session cookie |

Never commit `.env`, cookies, tokens, real referral-code lists, or browser HAR files.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | At least one valid code and no request errors |
| `1` | No valid code and no request errors |
| `2` | Invalid input or at least one request error |

## Development

Apply formatting and safe automated fixes:

```bash
uv run python scripts/quality.py format
```

Run the complete local gate:

```bash
uv run python scripts/quality.py
```

Run tests only:

```bash
uv run python scripts/quality.py test
```

The complete gate checks [Ruff](https://docs.astral.sh/ruff/),
[isort](https://pycqa.github.io/isort/),
[Pylint](https://pylint.readthedocs.io/en/latest/),
[mypy](https://mypy.readthedocs.io/en/stable/),
[Pyright](https://microsoft.github.io/pyright/),
[Bandit](https://bandit.readthedocs.io/en/latest/),
[pyscn](https://ludo-technologies.github.io/pyscn/), and
[pytest](https://docs.pytest.org/en/stable/), plus dependency-vulnerability
checks with [pip-audit](https://github.com/pypa/pip-audit) and package builds
with [uv build](https://docs.astral.sh/uv/reference/cli/#uv-build).
[GitHub Actions](https://docs.github.com/actions) runs the full gate on
[Python](https://www.python.org/) 3.12 and compatibility tests on Python 3.13,
Python 3.14, Windows, and macOS.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before
submitting changes or reporting a vulnerability.

## Prompts

You might be interested in the prompts I used to generate this.

First, I used the [Web UI version of ChatGPT](https://chatgpt.com) and selected `GPT-5.6 Sol` with the `high` reasoning level.

This was the first prompt:

```md
Write a program that accepts a Python list and tests all the referral codes in the provided list asynchronously using the queries provided in the GraphQL extraction file. Your Python code should use as many third-party libraries as possible to achieve the minimum number of lines of code while including the greatest number and coverage of features. For example:

* TUI
* GUI
* Asynchronous execution
* Logging, e.g., Loguru
* Rich
* Modern API libraries
* Use of decorators
* Modern GraphQL clients
* Use ruff check, ruff format, isort, pylint, mypy, pyscn (use all features listed in their documentation), and two more static analyzers
* Reproducible
* astral-uv
* pyproject.toml
* No suppression of warnings, notices, errors, etc.
* Cross-platform
* Use and adopt at least five different software engineering best practices, design patterns, etc.
* Unit tests, if deemed appropriate
* CI/CD, if deemed appropriate

Spend at least [30 minutes] actively working on this task before providing the final answer. Count only productive task work, not idle time, waiting, sleep commands, artificial delays, or time spent merely keeping a timer running. Use timing utilities only to measure elapsed time, and briefly report how you measured it.
```

This was the second prompt:

```md
Now, take the perspective of an open-source project maintainer. Please remove all of the following from the codebase and perform code-line cleanup and removal:

* Commentary
* Legacy Python support, e.g., future annotations. We support only Python 3.12 or above.
* Unnecessary, generic, and overly easy test files
* Empty directories
* I don't think we need to manually configure that many linting rules in pyproject.toml. Remove most of the default, unnecessary, and harmful ones.
* Any files, documentation, and commentary that are completely unrelated to or do not aid the goal of "making this an open-source project and helping others set up, install, deploy, and run it"
* I think your CI/CD tooling script and YAML file contain duplications. Please deduplicate them.
* Please run all linting and formatting tools again after fixing these issues, and perform a codebase-wide cleanup sweep.
```

Afterward, I downloaded the resulting codebase to a local directory, deployed it, and spotted two bugs affecting functionality and two issues affecting codebase quality:

1. In NiceGUI, results do not render in the table.
2. Fetching and querying do not fail fast when credential errors occur.
3. Rerunning the pre-commit hook fails due to unfixed linting issues.
4. GitHub CI/CD was failing because of test-case errors that were masked in the local environment when `Cookie` was set.

I spotted these issues sequentially and launched `GPT-5.6 Terra Ultra` to fix them. I did not choose `GPT-5.6 Sol` because I wanted to try `Ultra` mode with Terra specifically, and I knew that the `Sol + Ultra` combination would deplete my weekly credits very quickly.

Afterward, we arrived at the third commit on GitHub.
