"""Tests for LNT005 (http-timeout) rule."""

from __future__ import annotations

import ast
from pathlib import Path

from rivt.models import RivtConfig
from rivt.rules.http_timeout import HttpTimeoutRule


def _make_config() -> RivtConfig:
    return RivtConfig(
        preset="fastapi",
        config_module="app/core/config.py",
        orm="sqlalchemy",
        http_client="httpx",
        exclude=[],
        disable=[],
        layers={},
        library_layer_map={},
    )


def test_httpx_get_without_timeout_flagged() -> None:
    """httpx.get() without timeout should be flagged."""
    source = """
import httpx

response = httpx.get("https://api.example.com")
"""
    tree = ast.parse(source)
    rule = HttpTimeoutRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/clients/stripe.py"), config)

    assert len(violations) == 1
    assert violations[0].rule_id == "LNT005"
    assert "Add timeout parameter to httpx.get()" in violations[0].message


def test_httpx_get_with_timeout_clean() -> None:
    """httpx.get(timeout=10) should have no violation."""
    source = """
import httpx

response = httpx.get("https://api.example.com", timeout=10)
"""
    tree = ast.parse(source)
    rule = HttpTimeoutRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/clients/stripe.py"), config)

    assert len(violations) == 0


def test_httpx_client_without_timeout_flagged() -> None:
    """httpx.Client() without timeout should be flagged."""
    source = """
import httpx

client = httpx.Client()
"""
    tree = ast.parse(source)
    rule = HttpTimeoutRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/clients/stripe.py"), config)

    assert len(violations) == 1
    assert violations[0].rule_id == "LNT005"
    assert "Add timeout parameter to httpx.Client()" in violations[0].message


def test_httpx_client_with_timeout_clean() -> None:
    """httpx.Client(timeout=10) should have no violation."""
    source = """
import httpx

client = httpx.Client(timeout=10)
"""
    tree = ast.parse(source)
    rule = HttpTimeoutRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/clients/stripe.py"), config)

    assert len(violations) == 0


def test_client_instance_get_not_flagged() -> None:
    """client.get() (method on instance) should NOT be flagged."""
    source = """
import httpx

client = httpx.Client(timeout=10)
response = client.get("https://api.example.com")
"""
    tree = ast.parse(source)
    rule = HttpTimeoutRule()
    config = _make_config()
    violations = rule.check(tree, Path("app/clients/stripe.py"), config)

    assert len(violations) == 0


def _make_requests_config() -> RivtConfig:
    return RivtConfig(
        preset="fastapi",
        config_module="app/core/config.py",
        orm="sqlalchemy",
        http_client="requests",
        exclude=[],
        disable=[],
        layers={},
        library_layer_map={},
    )


def test_requests_session_without_timeout_flagged() -> None:
    """requests.Session() without timeout should be flagged."""
    source = """
import requests

session = requests.Session()
"""
    tree = ast.parse(source)
    rule = HttpTimeoutRule()
    config = _make_requests_config()
    violations = rule.check(tree, Path("app/clients/stripe.py"), config)

    assert len(violations) == 1
    assert "requests.Session()" in violations[0].message


def test_requests_get_without_timeout_flagged() -> None:
    """requests.get() without timeout should be flagged."""
    source = """
import requests

response = requests.get("https://api.example.com")
"""
    tree = ast.parse(source)
    rule = HttpTimeoutRule()
    config = _make_requests_config()
    violations = rule.check(tree, Path("app/clients/stripe.py"), config)

    assert len(violations) == 1
    assert "requests.get()" in violations[0].message
