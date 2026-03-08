"""Tests for LNT002 (no-env-vars) rule."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import RivtConfig
from rivt.rules.no_env_vars import NoEnvVarsRule


def _make_config(config_module: str = "app/core/config.py") -> RivtConfig:
    return RivtConfig(
        preset="fastapi",
        config_module=config_module,
        orm="sqlalchemy",
        http_client="httpx",
        exclude=[],
        disable=[],
        layers={},
        library_layer_map={},
    )


def test_os_getenv_flagged() -> None:
    """os.getenv() should be flagged."""
    source = """
import os

def foo():
    api_key = os.getenv("API_KEY")
"""
    tree = ast.parse(source)
    rule = NoEnvVarsRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/services/email.py"), config)

    assert len(violations) == 1
    assert violations[0].rule_id == "LNT002"
    assert "Do not access environment variables directly" in violations[0].message
    assert "app/core/config.py" in violations[0].message


def test_os_environ_get_flagged() -> None:
    """os.environ.get() should be flagged."""
    source = """
import os

def foo():
    key = os.environ.get("API_KEY")
"""
    tree = ast.parse(source)
    rule = NoEnvVarsRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/services/email.py"), config)

    assert len(violations) == 1
    assert violations[0].rule_id == "LNT002"


def test_os_environ_flagged() -> None:
    """os.environ access should be flagged."""
    source = """
import os

def foo():
    key = os.environ["API_KEY"]
"""
    tree = ast.parse(source)
    rule = NoEnvVarsRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/services/email.py"), config)

    assert len(violations) >= 1
    assert any(v.rule_id == "LNT002" for v in violations)
    assert any("Do not access environment variables directly" in v.message for v in violations)


def test_config_module_file_skipped() -> None:
    """The config module file itself should not be checked."""
    source = """
import os

def get_settings():
    return os.getenv("DATABASE_URL")
"""
    tree = ast.parse(source)
    rule = NoEnvVarsRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/core/config.py"), config)

    assert len(violations) == 0


def test_no_os_usage_clean() -> None:
    """Code without os.environ/os.getenv should have no violations."""
    source = """
from app.core.config import settings

def foo():
    api_key = settings.api_key
"""
    tree = ast.parse(source)
    rule = NoEnvVarsRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/services/email.py"), config)

    assert len(violations) == 0
