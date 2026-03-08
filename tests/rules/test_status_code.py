"""Tests for LNT004 — status-code rule."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from rivt.rules.status_code import StatusCodeRule


@pytest.fixture
def rule() -> StatusCodeRule:
    return StatusCodeRule()


def test_post_without_status_code_is_violation(rule, fastapi_config):
    """POST without status_code is a violation."""
    source = """
@router.post("/users", response_model=UserResponse)
def create_user(data: CreateUserRequest):
    return user_service.create(data)
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
    assert len(violations) == 1
    assert violations[0].rule_id == "LNT004"
    assert "status_code=201" in violations[0].message


def test_delete_without_status_code_is_violation(rule, fastapi_config):
    """DELETE without status_code is a violation, and suggests 204."""
    source = """
@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    user_service.delete(user_id)
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
    assert len(violations) == 1
    assert violations[0].rule_id == "LNT004"
    assert "status_code=204" in violations[0].message


def test_get_without_status_code_is_not_violation(rule, fastapi_config):
    """GET without status_code is NOT a violation."""
    source = """
@router.get("/users/{user_id}")
def get_user(user_id: int):
    return user_service.get(user_id)
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
    assert len(violations) == 0


def test_put_patch_without_status_code_are_not_violations(rule, fastapi_config):
    """PUT and PATCH without status_code are NOT violations."""
    for method in ("put", "patch"):
        source = f"""
@router.{method}("/users/{{user_id}}", response_model=UserResponse)
def update_user(user_id: int, data: UpdateUserRequest):
    return user_service.update(user_id, data)
"""
        tree = ast.parse(source)
        violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
        assert len(violations) == 0, f"Expected no violation for @router.{method}"


def test_post_with_status_code_is_clean(rule, fastapi_config):
    """POST with status_code is clean."""
    source = """
@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(data: CreateUserRequest):
    return user_service.create(data)
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
    assert len(violations) == 0


def test_delete_with_status_code_is_clean(rule, fastapi_config):
    """DELETE with status_code is clean."""
    source = """
@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    user_service.delete(user_id)
"""
    tree = ast.parse(source)
    violations = rule.check(tree, Path("app/routers/users.py"), fastapi_config)
    assert len(violations) == 0
