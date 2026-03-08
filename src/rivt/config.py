from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import TypedDict

from rivt.models import LayerConfig, RivtConfig


class _LayerDef(TypedDict):
    can_import_from: list[str]


class _PresetConfig(TypedDict):
    layers: dict[str, _LayerDef]
    library_layer_map: dict[str, list[str]]
    defaults: dict[str, str]


PRESETS: dict[str, _PresetConfig] = {
    "fastapi": {
        "layers": {
            "routers": {"can_import_from": ["services", "schemas"]},
            "services": {"can_import_from": ["repositories", "clients", "schemas"]},
            "repositories": {"can_import_from": ["schemas", "models"]},
            "clients": {"can_import_from": ["schemas"]},
            "schemas": {"can_import_from": []},
            "models": {"can_import_from": []},
        },
        "library_layer_map": {
            "fastapi": ["routers"],
        },
        "defaults": {
            "orm": "sqlalchemy",
            "http_client": "httpx",
        },
    },
}


def find_project_root(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    while True:
        if (current / "pyproject.toml").is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_config(project_root: Path) -> RivtConfig:
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.is_file():
        print("Error: No pyproject.toml found. Run 'rivt init' to create one.", file=sys.stderr)
        sys.exit(2)

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    tool_config = pyproject.get("tool", {}).get("rivt")
    if tool_config is None:
        print(
            "Error: No [tool.rivt] section in pyproject.toml. Run 'rivt init' to create one.",
            file=sys.stderr,
        )
        sys.exit(2)

    preset_name = tool_config.get("preset")
    if preset_name is None:
        print("Error: 'preset' is required in [tool.rivt].", file=sys.stderr)
        sys.exit(2)

    if preset_name not in PRESETS:
        available = ", ".join(sorted(PRESETS))
        print(f"Error: Unknown preset '{preset_name}'. Available: {available}.", file=sys.stderr)
        sys.exit(2)

    preset = PRESETS[preset_name]

    user_paths = tool_config.get("paths", {})
    config_module = user_paths.get("config_module", "")
    orm = tool_config.get("orm", preset["defaults"].get("orm", ""))
    http_client = tool_config.get("http_client", preset["defaults"].get("http_client", ""))
    exclude = tool_config.get("exclude", [])
    disable = tool_config.get("disable", [])

    layers: dict[str, LayerConfig] = {}
    for layer_name, layer_def in preset["layers"].items():
        paths = user_paths.get(layer_name)
        if paths is None:
            continue
        if isinstance(paths, str):
            paths = [paths]
        layers[layer_name] = LayerConfig(
            name=layer_name,
            paths=paths,
            can_import_from=layer_def["can_import_from"],
        )

    library_layer_map: dict[str, list[str]] = dict(preset.get("library_layer_map", {}))
    if orm:
        library_layer_map[orm] = ["repositories", "models"]
    if http_client:
        library_layer_map[http_client] = ["clients"]

    _validate_no_overlapping_paths(layers)

    return RivtConfig(
        preset=preset_name,
        config_module=config_module,
        orm=orm,
        http_client=http_client,
        exclude=exclude,
        disable=disable,
        layers=layers,
        library_layer_map=library_layer_map,
    )


def _validate_no_overlapping_paths(layers: dict[str, LayerConfig]) -> None:
    seen: list[tuple[str, str]] = []
    for layer in layers.values():
        for p in layer.paths:
            p_parts = Path(p).parts
            for existing_name, existing_path in seen:
                e_parts = Path(existing_path).parts
                if p_parts[: len(e_parts)] == e_parts or e_parts[: len(p_parts)] == p_parts:
                    print(
                        f"Error: Overlapping layer paths: '{layer.name}' ({p}) "
                        f"and '{existing_name}' ({existing_path}).",
                        file=sys.stderr,
                    )
                    sys.exit(2)
            seen.append((layer.name, p))
