"""Static checks for oracle/decision-path separation (AI-6)."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import pkgutil
from pathlib import Path
from typing import Iterable

from revive.benchmark import BASELINE_MODULES, DECISION_PATH_MODULES, ORACLE_MODULE

FORBIDDEN_ORACLE_MODULES = frozenset(
    {
        "revive.simulation.oracle",
        "revive.simulation.oracle._partition",
        "revive.simulation.oracle.resolve",
        "revive.simulation.latent",
    }
)


def decision_path_module_names() -> tuple[str, ...]:
    names: list[str] = []
    for root in DECISION_PATH_MODULES:
        names.append(root)
        try:
            pkg = importlib.import_module(root)
        except ImportError:
            continue
        if hasattr(pkg, "__path__"):
            for mod in pkgutil.walk_packages(pkg.__path__, prefix=f"{root}."):
                names.append(mod.name)
    return tuple(sorted(set(names)))


def _module_imports_forbidden(module_name: str) -> list[str]:
    path = _source_path(module_name)
    if path is None or not path.exists():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden(alias.name):
                    forbidden.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if _is_forbidden(node.module):
                forbidden.append(node.module)
    return forbidden


def _is_forbidden(module: str) -> bool:
    for forbidden in FORBIDDEN_ORACLE_MODULES:
        if module == forbidden or module.startswith(forbidden + "."):
            return True
    return False


def _source_path(module_name: str) -> Path | None:
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ModuleNotFoundError, ValueError):
        return None
    if spec is None or spec.origin is None or spec.origin == "built-in":
        return None
    return Path(spec.origin)


def baseline_module_names() -> tuple[str, ...]:
    names: list[str] = []
    for root in BASELINE_MODULES:
        names.append(root)
        try:
            pkg = importlib.import_module(root)
        except ImportError:
            continue
        if hasattr(pkg, "__path__"):
            for mod in pkgutil.walk_packages(pkg.__path__, prefix=f"{root}."):
                names.append(mod.name)
    return tuple(sorted(set(names)))


def assert_modules_do_not_import_oracle(modules: Iterable[str]) -> None:
    for name in modules:
        forbidden = _module_imports_forbidden(name)
        if forbidden:
            raise AssertionError(f"{name} imports forbidden oracle modules: {forbidden}")
        mod = importlib.import_module(name)
        if ORACLE_MODULE in getattr(mod, "__dict__", {}):
            raise AssertionError(f"{name} binds oracle symbol")


def assert_decision_path_does_not_import_oracle(
    decision_modules: Iterable[str] | None = None,
) -> None:
    """Raise AssertionError if decision-path modules import oracle internals."""
    assert_modules_do_not_import_oracle(decision_modules or decision_path_module_names())


def assert_baseline_modules_do_not_import_oracle(
    baseline_modules: Iterable[str] | None = None,
) -> None:
    """Raise AssertionError if baseline modules import oracle internals."""
    assert_modules_do_not_import_oracle(baseline_modules or baseline_module_names())
