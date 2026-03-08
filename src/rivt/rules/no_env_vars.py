"""LNT002: Disallow direct access to environment variables outside config module."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import RivtConfig, Violation
from rivt.rules import Rule


def _normalize_path(path: Path | str) -> str:
    """Normalize path for comparison (forward slashes)."""
    return str(path).replace("\\", "/")


class NoEnvVarsRule(Rule):
    """LNT002: Read from config module instead of os.environ/os.getenv."""

    id = "LNT002"
    name = "no-env-vars"

    def check(self, tree: ast.Module, file_path: Path, config: RivtConfig) -> list[Violation]:
        file_path_norm = _normalize_path(file_path)
        config_module_norm = _normalize_path(config.config_module) if config.config_module else ""
        if config_module_norm and file_path_norm == config_module_norm:
            return []

        violations: list[Violation] = []
        seen: set[tuple[int, int]] = set()
        msg = self._message(config)

        def add_violation(line: int, col: int) -> None:
            key = (line, col)
            if key not in seen:
                seen.add(key)
                violations.append(
                    Violation(
                        rule_id=self.id,
                        path=str(file_path),
                        line=line,
                        col=col,
                        message=msg,
                    )
                )

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                func = node.func
                # os.getenv(...)
                if (
                    isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                    and func.attr == "getenv"
                ):
                    add_violation(node.lineno, node.col_offset)
                    continue

                # os.environ.get(...)
                if (
                    isinstance(func.value, ast.Attribute)
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id == "os"
                    and func.value.attr == "environ"
                    and func.attr == "get"
                ):
                    add_violation(node.lineno, node.col_offset)
                    continue

            # os.environ attribute access
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
                and node.attr == "environ"
            ):
                add_violation(node.lineno, node.col_offset)

            # os.environ["KEY"]
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Attribute)
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "os"
                and node.value.attr == "environ"
            ):
                add_violation(node.lineno, node.col_offset)

        return violations

    def _message(self, config: RivtConfig) -> str:
        if config.config_module:
            return (
                "Do not access environment variables directly."
                f" Read from the config module instead ({config.config_module})."
            )
        return "Do not access environment variables directly. Read from the config module instead."
