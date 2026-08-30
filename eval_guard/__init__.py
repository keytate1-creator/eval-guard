"""
EvalGuard: High-Throughput Deterministic Constraint & AST Evaluation Engine.
Zero-dependency, production-grade static evaluation suite.
"""

from eval_guard.core import RuleEngine, EvaluationContext, EvaluationReport, Violation
from eval_guard.constraints import (
    BaseConstraint,
    ForbiddenImportsConstraint,
    MaxCyclomaticComplexityConstraint,
    TokenBudgetConstraint,
    RegexNegativeConstraint,
    RegexPositiveConstraint,
    MaxNestingDepthConstraint,
)

__version__ = "0.1.0"
__author__ = "Kaylor Tate Cespedes"

__all__ = [
    "RuleEngine",
    "EvaluationContext",
    "EvaluationReport",
    "Violation",
    "BaseConstraint",
    "ForbiddenImportsConstraint",
    "MaxCyclomaticComplexityConstraint",
    "TokenBudgetConstraint",
    "RegexNegativeConstraint",
    "RegexPositiveConstraint",
    "MaxNestingDepthConstraint",
]
