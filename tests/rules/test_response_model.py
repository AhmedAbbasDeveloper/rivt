"""Tests for LNT003 — response-model rule."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from rivt.rules.response_model import ResponseModelRule


@pytest.fixture
def rule() -> ResponseModelRule:
    return ResponseModelRule()


def test_violation_when_neither_response_model_nor_return_type(rule, fastapi_config):
    """Route with neither response_model nor return type annotation is a violation."""
    source = """
@router.get("/users/{user_id}")
def get_user(user_id: int):
    return user_service.get(user_id)
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
    assert len(violations) == 1
    assert violations[0].rule_id == "LNT003"
    assert violations[0].path == "app/routers/users.py"
    assert violations[0].line == 3
    assert "response_model" in violations[0].message
    assert "return type annotation" in violations[0].message


def test_clean_when_response_model_present(rule, fastapi_config):
    """Route with response_model in decorator is clean."""
    source = """
@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    return user_service.get(user_id)
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
    assert len(violations) == 0


def test_clean_when_return_type_annotation_present(rule, fastapi_config):
    """Route with return type annotation is clean."""
    source = """
@router.get("/users/{user_id}")
def get_user(user_id: int) -> UserResponse:
    return user_service.get(user_id)
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
    assert len(violations) == 0


def test_non_route_decorated_functions_not_flagged(rule, fastapi_config):
    """Functions without route decorators are not flagged."""
    source = """
def plain_function(x: int):
    return x * 2

@some_other_decorator
def decorated_but_not_route():
    pass
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/services/helper.py"), fastapi_config)
    assert len(violations) == 0


def test_async_function_handlers(rule, fastapi_config):
    """Async route handlers work the same as sync."""
    source = """
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    return await user_service.get(user_id)
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
    assert len(violations) == 1

    # With return type, should be clean
    source_clean = """
@router.get("/users/{user_id}")
async def get_user(user_id: int) -> UserResponse:
    return await user_service.get(user_id)
"""
    tree_clean = ast.parse(source_clean)
    violations_clean = rule.check(tree_clean, Path("app/routers/users.py"), fastapi_config)
    assert len(violations_clean) == 0
