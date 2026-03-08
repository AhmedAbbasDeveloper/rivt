"""Tests for LNT001 layer-imports rule."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from rivt.models import LayerConfig, RivtConfig
from rivt.rules.layer_imports import LayerImportsRule


def _check(code: str, file_path: Path, config: RivtConfig):
    """Parse code and run LNT001, returning violations."""
    tree = ast.parse(code)
    rule = LayerImportsRule()
    return rule.check(tree, file_path, config)


class TestLayerToLayerViolation:
    """Tests for layer-to-layer import restrictions."""

    def test_routers_importing_from_repositories(self, fastapi_config: RivtConfig) -> None:
        code = """
# app/routers/users.py
from app.repositories.user import get_user_by_id

@router.get("/users/{user_id}")
def get_user(user_id: int):
    return get_user_by_id(user_id)
"""
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_id == "LNT001"
        assert "Routers must not import from repositories" in v.message
        assert "Import from services, schemas instead" in v.message
        assert "(found: app.repositories.user)" in v.message
        assert v.line == 3
        assert v.path == "app/routers/users.py"

    def test_routers_importing_from_services_allowed(self, fastapi_config: RivtConfig) -> None:
        code = """
# app/routers/users.py
from app.services.user import get_user

@router.get("/users/{user_id}")
def get_user_route(user_id: int):
    return get_user(user_id)
"""
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 0

    def test_relative_import_repositories_from_router(self, fastapi_config: RivtConfig) -> None:
        """Relative import ..repositories in a router file is a violation."""
        code = """
# app/routers/users.py
from ..repositories.user import get_user_by_id

def get_user(user_id: int):
    return get_user_by_id(user_id)
"""
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 1
        assert "repositories" in violations[0].message


class TestLibraryRestrictionViolation:
    """Tests for library restriction violations."""

    def test_services_importing_fastapi(self, fastapi_config: RivtConfig) -> None:
        code = """
# app/services/order.py
from fastapi import HTTPException

def cancel_order(order_id: int):
    order = get_order(order_id)
    if order.status == "shipped":
        raise HTTPException(status_code=400, detail="Cannot cancel shipped order")
"""
        violations = _check(code, Path("app/services/order.py"), fastapi_config)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule_id == "LNT001"
        assert "Services must not import fastapi" in v.message
        assert "Raise a domain exception" in v.message
        assert "(found: fastapi.HTTPException)" in v.message
        assert v.line == 3

    def test_services_importing_domain_exception_allowed(
        self, fastapi_config: RivtConfig
    ) -> None:
        code = """
# app/services/order.py
from app.exceptions import OrderCancelError

def cancel_order(order_id: int):
    order = get_order(order_id)
    if order.status == "shipped":
        raise OrderCancelError("Cannot cancel shipped order")
"""
        violations = _check(code, Path("app/services/order.py"), fastapi_config)
        assert len(violations) == 0

    def test_routers_importing_sqlalchemy(self, fastapi_config: RivtConfig) -> None:
        """SQLAlchemy is restricted to repositories layer."""
        code = """
# app/routers/users.py
from sqlalchemy.orm import Session

def get_users():
    pass
"""
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 1
        assert "sqlalchemy" in violations[0].message.lower()
        assert "repositories" in violations[0].message

    def test_services_importing_httpx(self, fastapi_config: RivtConfig) -> None:
        """httpx is restricted to clients layer."""
        code = """
# app/services/notification.py
import httpx

def send_notification(url: str):
    httpx.get(url)
"""
        violations = _check(code, Path("app/services/notification.py"), fastapi_config)
        assert len(violations) == 1
        assert "httpx" in violations[0].message.lower()


class TestCleanImports:
    """Tests for allowed/clean imports."""

    def test_repositories_import_sqlalchemy(self, fastapi_config: RivtConfig) -> None:
        code = """
# app/repositories/user.py
from sqlalchemy.orm import Session

def get_user_by_id(session: Session, user_id: int):
    return session.query(User).filter_by(id=user_id).first()
"""
        violations = _check(code, Path("app/repositories/user.py"), fastapi_config)
        assert len(violations) == 0

    def test_clients_import_httpx(self, fastapi_config: RivtConfig) -> None:
        code = """
# app/clients/stripe.py
import httpx

def get_charges():
    return httpx.get("https://api.stripe.com/v1/charges", timeout=10)
"""
        violations = _check(code, Path("app/clients/stripe.py"), fastapi_config)
        assert len(violations) == 0

    def test_routers_import_fastapi(self, fastapi_config: RivtConfig) -> None:
        code = """
# app/routers/users.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def list_users():
    return []
"""
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 0


class TestFileNotInLayer:
    """Tests for files outside configured layers."""

    def test_file_not_in_any_layer_returns_empty(self, fastapi_config: RivtConfig) -> None:
        code = """
# scripts/something.py (not in any layer)
from app.repositories.user import get_user
from fastapi import APIRouter
"""
        violations = _check(code, Path("scripts/something.py"), fastapi_config)
        assert len(violations) == 0

    def test_app_core_file_not_in_layer(self, fastapi_config: RivtConfig) -> None:
        code = """
# app/core/config.py
import os
os.getenv("FOO")
"""
        violations = _check(code, Path("app/core/config.py"), fastapi_config)
        assert len(violations) == 0


class TestStarImports:
    """Tests for star imports."""

    def test_star_import_checked_by_source_module(self, fastapi_config: RivtConfig) -> None:
        """Star imports are checked by their source module."""
        code = """
# app/routers/users.py
from app.repositories import *

def get_user(user_id: int):
    return get_user_by_id(user_id)
"""
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 1
        assert "repositories" in violations[0].message
        assert "(found: app.repositories)" in violations[0].message


class TestSchemasAndModelsLayers:
    """Tests for schemas and models layer enforcement."""

    def test_service_importing_schemas_allowed(self, fastapi_config: RivtConfig) -> None:
        code = """
from app.schemas.user import UserResponse

def get_user(user_id: int) -> UserResponse:
    pass
"""
        violations = _check(code, Path("app/services/user.py"), fastapi_config)
        assert len(violations) == 0

    def test_router_importing_schemas_allowed(self, fastapi_config: RivtConfig) -> None:
        code = """
from app.schemas.user import UserResponse
"""
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 0

    def test_repository_importing_models_allowed(self, fastapi_config: RivtConfig) -> None:
        code = """
from app.models.user import UserModel

def get_user_by_id(user_id: int):
    pass
"""
        violations = _check(code, Path("app/repositories/user.py"), fastapi_config)
        assert len(violations) == 0

    def test_service_importing_models_is_violation(self, fastapi_config: RivtConfig) -> None:
        code = """
from app.models.user import UserModel

def get_user(user_id: int):
    pass
"""
        violations = _check(code, Path("app/services/user.py"), fastapi_config)
        assert len(violations) == 1
        assert "models" in violations[0].message

    def test_router_importing_models_is_violation(self, fastapi_config: RivtConfig) -> None:
        code = """
from app.models.user import UserModel
"""
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 1
        assert "models" in violations[0].message

    def test_client_importing_models_is_violation(self, fastapi_config: RivtConfig) -> None:
        code = """
from app.models.user import UserModel
"""
        violations = _check(code, Path("app/clients/user.py"), fastapi_config)
        assert len(violations) == 1
        assert "models" in violations[0].message

    def test_client_importing_schemas_allowed(self, fastapi_config: RivtConfig) -> None:
        code = """
from app.schemas.webhook import WebhookPayload
"""
        violations = _check(code, Path("app/clients/stripe.py"), fastapi_config)
        assert len(violations) == 0


class TestRelativeImports:
    """Tests for relative import resolution."""

    def test_relative_import_same_package(self, fastapi_config: RivtConfig) -> None:
        """from .foo in app/routers/users.py imports from app.routers.foo (same layer)."""
        code = """
# app/routers/users.py
from .common import router_helper

def get_user(user_id: int):
    return router_helper(user_id)
"""
        # app.routers.common is in routers layer - same layer, allowed
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 0

    def test_relative_import_parent_services_from_router(
        self, fastapi_config: RivtConfig
    ) -> None:
        """from ..services in app/routers/users.py -> app.services (allowed)."""
        code = """
# app/routers/users.py
from ..services.user import get_user

def get_user_route(user_id: int):
    return get_user(user_id)
"""
        violations = _check(code, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 0


class TestSingleFileLayer:
    """Tests for single-file layer paths (e.g. models = 'src/models.py')."""

    @pytest.fixture
    def single_file_models_config(self) -> RivtConfig:
        return RivtConfig(
            preset="fastapi",
            config_module="src/settings.py",
            orm="sqlalchemy",
            http_client="httpx",
            exclude=[],
            disable=[],
            layers={
                "routers": LayerConfig(
                    name="routers",
                    paths=["src/api/routers"],
                    can_import_from=["services", "schemas"],
                ),
                "services": LayerConfig(
                    name="services",
                    paths=["src/services"],
                    can_import_from=["repositories", "clients", "schemas"],
                ),
                "repositories": LayerConfig(
                    name="repositories",
                    paths=["src/repositories"],
                    can_import_from=["schemas", "models"],
                ),
                "clients": LayerConfig(
                    name="clients",
                    paths=["src/clients"],
                    can_import_from=["schemas"],
                ),
                "models": LayerConfig(
                    name="models",
                    paths=["src/models.py"],
                    can_import_from=[],
                ),
            },
            library_layer_map={
                "fastapi": ["routers"],
                "sqlalchemy": ["repositories", "models"],
                "httpx": ["clients"],
            },
        )

    def test_service_importing_single_file_models_is_violation(
        self, single_file_models_config: RivtConfig
    ) -> None:
        code = """
from src.models import User
"""
        violations = _check(code, Path("src/services/user.py"), single_file_models_config)
        assert len(violations) == 1
        assert "models" in violations[0].message

    def test_repository_importing_single_file_models_allowed(
        self, single_file_models_config: RivtConfig
    ) -> None:
        code = """
from src.models import User
"""
        violations = _check(code, Path("src/repositories/user.py"), single_file_models_config)
        assert len(violations) == 0

    def test_single_file_models_itself_is_in_layer(
        self, single_file_models_config: RivtConfig
    ) -> None:
        """The models.py file itself should be recognized as the models layer."""
        code = """
from sqlalchemy import Column, Integer, String
"""
        violations = _check(code, Path("src/models.py"), single_file_models_config)
        assert len(violations) == 0
