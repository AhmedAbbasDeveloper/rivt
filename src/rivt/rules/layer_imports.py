"""LNT001: Enforce import boundaries between architectural layers."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import LayerConfig, RivtConfig, Violation
from rivt.rules import Rule


def _resolve_relative_import(file_path: Path, level: int, module: str | None) -> str:
    """Resolve a relative import to an absolute module path.

    file_path is relative to project root (e.g. app/routers/users.py).
    level is the number of leading dots (1 = current package, 2 = parent, etc.).
    """
    dir_path = file_path.parent
    parts = list(dir_path.parts)

    if level < 1:
        raise ValueError("Relative import level must be >= 1")

    num_up = level - 1
    base_parts = parts[: len(parts) - num_up] if num_up < len(parts) else []

    base_module = ".".join(base_parts) if base_parts else ""
    if module:
        return f"{base_module}.{module}" if base_module else module
    return base_module


def _module_path_to_layer(module_path: str, config: RivtConfig) -> LayerConfig | None:
    """Map an absolute module path to its layer by prefix-matching layer paths."""
    path_str = module_path.replace(".", "/")

    best_match: LayerConfig | None = None
    best_len = -1

    for layer in config.layers.values():
        for layer_path in layer.paths:
            if layer_path.endswith(".py"):
                is_match = path_str == layer_path[:-3]
            else:
                is_match = path_str == layer_path or path_str.startswith(layer_path + "/")
            if is_match and len(layer_path) > best_len:
                best_len = len(layer_path)
                best_match = layer

    return best_match


def _get_layer_suggestion(layer: LayerConfig) -> str:
    """Get a suggestion for layer-to-layer violations."""
    if not layer.can_import_from:
        return "This layer cannot import from other layers."
    names = ", ".join(layer.can_import_from)
    return f"Import from {names} instead."


def _get_library_violation_message(
    current_layer: str, library: str, allowed_layers: list[str], found: str
) -> str:
    """Get error message for library restriction violations."""
    if library == "fastapi" and current_layer == "services":
        return (
            "Services must not import fastapi. Raise a domain exception and "
            f"handle it in the router layer. (found: {found})"
        )
    layers_str = ", ".join(allowed_layers)
    return (
        f"{current_layer.capitalize()} must not import {library}. "
        f"{library.capitalize()} is restricted to the {layers_str} layer. "
        f"(found: {found})"
    )


class LayerImportsRule(Rule):
    """LNT001: Enforce import boundaries between architectural layers."""

    id = "LNT001"
    name = "layer-imports"

    def check(self, tree: ast.Module, file_path: Path, config: RivtConfig) -> list[Violation]:
        current_layer = config.get_layer(file_path)
        if current_layer is None:
            return []

        violations: list[Violation] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_path = alias.name
                    self._check_import(
                        file_path,
                        module_path,
                        module_path,
                        node.lineno,
                        node.col_offset,
                        current_layer,
                        config,
                        violations,
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    try:
                        module_path = _resolve_relative_import(file_path, node.level, node.module)
                    except (ValueError, IndexError):
                        continue
                elif node.module:
                    module_path = node.module
                else:
                    continue

                if node.names:
                    first = node.names[0]
                    found = module_path if first.name == "*" else f"{module_path}.{first.name}"
                else:
                    found = module_path

                self._check_import(
                    file_path,
                    module_path,
                    found,
                    node.lineno,
                    node.col_offset,
                    current_layer,
                    config,
                    violations,
                )

        return violations

    def _check_import(
        self,
        file_path: Path,
        module_path: str,
        found: str,
        line: int,
        col: int,
        current_layer: LayerConfig,
        config: RivtConfig,
        violations: list[Violation],
    ) -> None:
        path_str = str(file_path)

        target_layer = _module_path_to_layer(module_path, config)
        if (
            target_layer is not None
            and target_layer.name != current_layer.name
            and target_layer.name not in current_layer.can_import_from
        ):
            suggestion = _get_layer_suggestion(current_layer)
            msg = (
                f"{current_layer.name.capitalize()} must not import from "
                f"{target_layer.name}. {suggestion} (found: {module_path})"
            )
            violations.append(
                Violation(
                    rule_id=self.id,
                    path=path_str,
                    line=line,
                    col=col,
                    message=msg,
                )
            )

        top_level = module_path.split(".")[0]
        if top_level in config.library_layer_map:
            allowed_layers = config.library_layer_map[top_level]
            if current_layer.name not in allowed_layers:
                msg = _get_library_violation_message(
                    current_layer.name, top_level, allowed_layers, found
                )
                violations.append(
                    Violation(
                        rule_id=self.id,
                        path=path_str,
                        line=line,
                        col=col,
                        message=msg,
                    )
                )
