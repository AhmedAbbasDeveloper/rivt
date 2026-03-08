from __future__ import annotations

import ast
from fnmatch import fnmatch
from pathlib import Path

from rivt.models import RivtConfig, Violation
from rivt.rules import ALL_RULES

ALWAYS_EXCLUDE = {".venv", "venv", ".git", "node_modules", "__pycache__", ".tox", ".eggs"}


def find_python_files(project_root: Path, config: RivtConfig) -> list[Path]:
    files: list[Path] = []
    for py_file in project_root.rglob("*.py"):
        rel_path = py_file.relative_to(project_root)

        if any(part in ALWAYS_EXCLUDE for part in rel_path.parts):
            continue

        rel_str = str(rel_path)
        if any(fnmatch(rel_str, pattern) for pattern in config.exclude):
            continue

        files.append(py_file)
    return sorted(files)


def run_checks(project_root: Path, config: RivtConfig) -> list[Violation]:
    active_rules = [r for r in ALL_RULES if r.id not in config.disable]

    all_violations: list[Violation] = []
    files = find_python_files(project_root, config)

    for py_file in files:
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue

        rel_path = py_file.relative_to(project_root)
        source_lines = source.splitlines()

        for rule in active_rules:
            for v in rule.check(tree, rel_path, config):
                if not _is_suppressed(v, source_lines):
                    all_violations.append(v)

    all_violations.sort(key=lambda v: (v.path, v.line, v.col))
    return all_violations


def _is_suppressed(violation: Violation, source_lines: list[str]) -> bool:
    line_idx = violation.line - 1
    if line_idx < 0 or line_idx >= len(source_lines):
        return False
    line = source_lines[line_idx]
    return f"# rivt: disable={violation.rule_id}" in line
