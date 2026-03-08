from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from pathlib import Path

from rivt.models import RivtConfig, Violation


class Rule(ABC):
    id: str
    name: str

    @abstractmethod
    def check(self, tree: ast.Module, file_path: Path, config: RivtConfig) -> list[Violation]: ...


from .http_timeout import HttpTimeoutRule
from .layer_imports import LayerImportsRule
from .no_env_vars import NoEnvVarsRule
from .response_model import ResponseModelRule
from .status_code import StatusCodeRule

ALL_RULES: list[Rule] = [
    LayerImportsRule(),
    NoEnvVarsRule(),
    ResponseModelRule(),
    StatusCodeRule(),
    HttpTimeoutRule(),
]
