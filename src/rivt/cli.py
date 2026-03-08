from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rivt.config import find_project_root, load_config
from rivt.reporter import format_violations
from rivt.runner import run_checks

_INIT_CONFIG = """\
[tool.rivt]
preset = "fastapi"

[tool.rivt.paths]
routers = "app/routers"
services = "app/services"
repositories = "app/repositories"
clients = "app/clients"
config_module = "app/core/config.py"
schemas = "app/schemas"
models = "app/models"
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rivt",
        description="Enforce architectural rules in your codebase.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("check", help="Check codebase for violations.")
    subparsers.add_parser("init", help="Initialize rivt configuration.")

    args = parser.parse_args()

    if args.command == "check":
        _run_check()
    elif args.command == "init":
        _run_init()
    else:
        parser.print_help()
        sys.exit(2)


def _run_check() -> None:
    project_root = find_project_root()
    if project_root is None:
        print("Error: Could not find pyproject.toml.", file=sys.stderr)
        sys.exit(2)

    config = load_config(project_root)
    violations = run_checks(project_root, config)

    if violations:
        print(format_violations(violations))
        sys.exit(1)
    else:
        print("No violations found.")
        sys.exit(0)


def _run_init() -> None:
    pyproject_path = Path.cwd() / "pyproject.toml"

    if pyproject_path.is_file():
        content = pyproject_path.read_text(encoding="utf-8")
        if "[tool.rivt]" in content:
            print("rivt is already configured in pyproject.toml.", file=sys.stderr)
            sys.exit(1)
        with open(pyproject_path, "a", encoding="utf-8") as f:
            if not content.endswith("\n"):
                f.write("\n")
            f.write("\n")
            f.write(_INIT_CONFIG)
    else:
        pyproject_path.write_text(_INIT_CONFIG, encoding="utf-8")

    print(f"Created rivt config in {pyproject_path}.")
    print("Edit the paths to match your project layout, then run: rivt check")
