#!/usr/bin/env python3
"""
Run the full development verification pipeline (check only, no auto-fix).

Steps: pyproject-fmt, black, isort, pip-audit, pylint, mypy, pytest, CLI --help smoke test.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
PYTHON_CHECK_PATHS = ("src", "tests", "scripts", "run.py")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger("verify")


@dataclass(frozen=True)
class VerifyStep:
    """A single verification command."""

    name: str
    command: list[str]


def _load_pyproject_tool_config(tool_name: str) -> dict[str, Any]:
    """Load a [tool.<name>] table from pyproject.toml."""
    if not PYPROJECT_PATH.is_file():
        logger.warning("pyproject.toml not found; skipping %s config", tool_name)
        return {}

    with PYPROJECT_PATH.open("rb") as pyproject_file:
        data = tomllib.load(pyproject_file)

    tool_config = data.get("tool", {}).get(tool_name, {})
    if not isinstance(tool_config, dict):
        logger.warning("Invalid [tool.%s] config; expected a table", tool_name)
        return {}
    return tool_config


def _build_pip_audit_command() -> list[str]:
    """Build pip-audit command using [tool.pip-audit] from pyproject.toml."""
    command = [sys.executable, "-m", "pip_audit", str(PROJECT_ROOT)]
    config = _load_pyproject_tool_config("pip-audit")

    progress_spinner = config.get("progress-spinner", "off")
    if progress_spinner:
        command.append(f"--progress-spinner={progress_spinner}")

    timeout = config.get("timeout")
    if timeout is not None:
        command.append(f"--timeout={timeout}")

    for vulnerability_id in config.get("ignore-vuln", []):
        command.extend(["--ignore-vuln", str(vulnerability_id)])

    for index_url in config.get("extra-index-url", []):
        command.extend(["--extra-index-url", str(index_url)])

    if config.get("require-hashes"):
        command.append("--require-hashes")

    if config.get("skip-editable"):
        command.append("--skip-editable")

    if config.get("no-deps"):
        command.append("--no-deps")

    return command


VERIFY_STEPS: tuple[VerifyStep, ...] = (
    VerifyStep(
        "pyproject-fmt",
        [sys.executable, "-m", "pyproject_fmt", "--check", str(PYPROJECT_PATH)],
    ),
    VerifyStep(
        "black",
        [sys.executable, "-m", "black", "--check", *PYTHON_CHECK_PATHS],
    ),
    VerifyStep(
        "isort",
        [sys.executable, "-m", "isort", "--check-only", *PYTHON_CHECK_PATHS],
    ),
    VerifyStep("pip-audit", _build_pip_audit_command()),
    VerifyStep("pylint", [sys.executable, "-m", "pylint", "src"]),
    VerifyStep("mypy", [sys.executable, "-m", "mypy", "src"]),
    VerifyStep("pytest", [sys.executable, "-m", "pytest", "tests/"]),
    VerifyStep("cli smoke", [sys.executable, "run.py", "cli", "--help"]),
)


def run_step(step: VerifyStep) -> bool:
    """Run one verification step and report pass or fail."""
    logger.info("=== %s ===", step.name)
    logger.info("Command: %s", " ".join(step.command))

    result = subprocess.run(
        step.command,
        cwd=PROJECT_ROOT,
        check=False,
    )

    if result.returncode == 0:
        logger.info("PASS: %s", step.name)
        return True

    logger.error("FAIL: %s (exit code %d)", step.name, result.returncode)
    return False


def main() -> int:
    """Run all verification steps and return a process exit code."""
    logger.info("FreeSMS verification (project root: %s)", PROJECT_ROOT)

    failures: list[str] = []
    for step in VERIFY_STEPS:
        if not run_step(step):
            failures.append(step.name)

    if failures:
        logger.error(
            "Verification FAILED (%d step(s)): %s",
            len(failures),
            ", ".join(failures),
        )
        return 1

    logger.info("Verification PASSED (all %d steps)", len(VERIFY_STEPS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
