"""
Oracle evaluator boundary — exports only outcome resolution.

Decision-path modules must NOT import this package.
"""

from revive.simulation.oracle.resolve import OutcomeResult, resolve_outcome

__all__ = ["OutcomeResult", "resolve_outcome"]
