from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Violation:
    rule_id: str
    path: str
    line: int
    col: int
    message: str


@dataclass
class LayerConfig:
    name: str
    paths: list[str]
    can_import_from: list[str]


@dataclass
class RivtConfig:
    preset: str
    config_module: str
    orm: str
    http_client: str
    exclude: list[str]
    disable: list[str]
    layers: dict[str, LayerConfig]
    library_layer_map: dict[str, list[str]]

    def get_layer(self, file_path: Path | str) -> LayerConfig | None:
        parts = Path(file_path).parts
        best_match: LayerConfig | None = None
        best_len = -1
        for layer in self.layers.values():
            for layer_path_str in layer.paths:
                layer_parts = Path(layer_path_str).parts
                if layer_path_str.endswith(".py"):
                    matched = parts == layer_parts
                else:
                    matched = (
                        len(parts) > len(layer_parts)
                        and parts[: len(layer_parts)] == layer_parts
                    )
                if matched and len(layer_parts) > best_len:
                    best_len = len(layer_parts)
                    best_match = layer
        return best_match
