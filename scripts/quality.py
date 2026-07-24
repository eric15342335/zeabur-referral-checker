import argparse
import subprocess
import sys
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[1]
type Command = tuple[str, ...]

PYTHON_PATHS = ("src", "tests", "scripts")

FORMAT_COMMANDS = (
    ("isort", *PYTHON_PATHS),
    ("ruff", "check", "--fix", "."),
    ("ruff", "format", "."),
)

TEST_COMMANDS = (("pytest",),)

CHECK_COMMANDS = (
    ("ruff", "check", "."),
    ("ruff", "format", "--check", "."),
    ("isort", "--check-only", "--diff", *PYTHON_PATHS),
    ("pylint", "src"),
    ("mypy", *PYTHON_PATHS),
    ("pyright",),
    ("bandit", "-r", "src"),
    ("pyscn", "check", "--max-complexity", "15", "--max-cycles", "0", "src"),
    *TEST_COMMANDS,
    ("pip-audit",),
    ("uv", "build"),
)


def run(commands: tuple[Command, ...]) -> None:
    missing = sorted({command[0] for command in commands if which(command[0]) is None})
    if missing:
        raise SystemExit(
            f"missing tools: {', '.join(missing)}; run uv sync --all-groups"
        )
    for command in commands:
        print(f"+ {' '.join(command)}", flush=True)
        subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "task", choices=("check", "format", "test"), nargs="?", default="check"
    )
    task = parser.parse_args().task
    commands = {
        "check": CHECK_COMMANDS,
        "format": FORMAT_COMMANDS,
        "test": TEST_COMMANDS,
    }
    run(commands[task])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
