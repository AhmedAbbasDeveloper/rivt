"""LNT005: Require timeout parameter on HTTP client calls."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import RivtConfig, Violation
from rivt.rules import Rule

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "request"}
HTTP_CLIENT_CONSTRUCTORS = {"Client", "AsyncClient", "Session"}


class HttpTimeoutRule(Rule):
    """LNT005: Add timeout to HTTP calls."""

    id = "LNT005"
    name = "http-timeout"

    def check(self, tree: ast.Module, file_path: Path, config: RivtConfig) -> list[Violation]:
        http_client = config.http_client
        if not http_client:
            return []

        violations: list[Violation] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if not isinstance(func.value, ast.Name):
                continue
            if func.value.id != http_client:
                continue

            attr = func.attr
            if attr not in HTTP_METHODS and attr not in HTTP_CLIENT_CONSTRUCTORS:
                continue

            if not any(kw.arg == "timeout" for kw in node.keywords):
                msg = f"Add timeout parameter to {http_client}.{attr}() (e.g. timeout=10)."
                violations.append(
                    Violation(
                        rule_id=self.id,
                        path=str(file_path),
                        line=node.lineno,
                        col=node.col_offset,
                        message=msg,
                    )
                )

        return violations
