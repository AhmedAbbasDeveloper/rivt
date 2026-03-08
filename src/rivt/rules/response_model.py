"""LNT003 — response-model: FastAPI route handlers must declare response type."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import RivtConfig, Violation
from rivt.rules import Rule

from .route_utils import get_route_decorators, has_keyword_arg


class ResponseModelRule(Rule):
    id = "LNT003"
    name = "response-model"

    def check(self, tree: ast.Module, file_path: Path, config: RivtConfig) -> list[Violation]:
        violations: list[Violation] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                violations.extend(self._check_function(node, file_path))
        return violations

    def _check_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path
    ) -> list[Violation]:
        violations: list[Violation] = []
        for decorator, _method in get_route_decorators(node):
            has_response_model = has_keyword_arg(decorator, "response_model")
            has_return_annotation = node.returns is not None
            if not has_response_model and not has_return_annotation:
                decorator_src = ast.unparse(decorator.func)
                msg = (
                    f"Add response_model to the @{decorator_src}() decorator"
                    " or a return type annotation (e.g. -> UserResponse)."
                )
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
