"""Pytest configuration and fixtures."""

import pytest

from rivt.models import LayerConfig, RivtConfig


@pytest.fixture
def fastapi_config() -> RivtConfig:
    """Create a FastAPI-like RivtConfig for testing."""
    return RivtConfig(
        preset="fastapi",
        config_module="app/core/config.py",
        orm="sqlalchemy",
        http_client="httpx",
        exclude=[],
        disable=[],
        layers={
            "routers": LayerConfig(
                name="routers",
                paths=["app/routers"],
                can_import_from=["services", "schemas"],
            ),
            "services": LayerConfig(
                name="services",
                paths=["app/services"],
                can_import_from=["repositories", "clients", "schemas"],
            ),
            "repositories": LayerConfig(
                name="repositories",
                paths=["app/repositories"],
                can_import_from=["schemas", "models"],
            ),
            "clients": LayerConfig(
                name="clients",
                paths=["app/clients"],
                can_import_from=["schemas"],
            ),
            "schemas": LayerConfig(
                name="schemas",
                paths=["app/schemas"],
                can_import_from=[],
            ),
            "models": LayerConfig(
                name="models",
                paths=["app/models"],
                can_import_from=[],
            ),
        },
        library_layer_map={
            "fastapi": ["routers"],
            "sqlalchemy": ["repositories", "models"],
            "httpx": ["clients"],
        },
    )
