"""
Core data structures and orchestration engine for EvalGuard.
"""

from __future__ import annotations

import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from eval_guard.constraints import BaseConstraint


@dataclass
class Violation:
    """Represents a specific rule or constraint violation."""
    rule_name: str
    message: str
    severity: str = "ERROR"  # "ERROR", "WARNING", "CRITICAL"
    line_number: Optional[int] = None
    penalty: float = 0.25

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "message": self.message,
            "severity": self.severity,
            "line_number": self.line_number,
            "penalty": self.penalty,
        }


@dataclass
class EvaluationContext:
    """Carries the code/text payload and runtime evaluation metadata."""
    payload: str
    language: str = "python"
    metadata: Dict[str, Any] = field(default_factory=dict)
    _cached_ast: Any = field(default=None, repr=False)

    @property
    def token_count(self) -> int:
        """Heuristic token count based on whitespace and punctuation splitting."""
        return len(self.payload.split())


@dataclass
class EvaluationReport:
    """Consolidated summary of an evaluation run."""
    passed: bool
    score: float
    violations: List[Violation] = field(default_factory=list)
    latency_us: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": round(self.score, 4),
            "latency_us": round(self.latency_us, 2),
            "total_violations": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class RuleEngine:
    """Deterministic evaluation orchestrator executing constraints against contexts."""

    def __init__(self, strict_mode: bool = False):
        self.constraints: List[BaseConstraint] = []
        self.strict_mode = strict_mode

    def add_constraint(self, constraint: BaseConstraint) -> RuleEngine:
        """Register a new constraint into the evaluation pipeline."""
        self.constraints.append(constraint)
        return self

    def clear_constraints(self) -> None:
        """Remove all registered constraints."""
        self.constraints.clear()

    def evaluate(self, context: EvaluationContext) -> EvaluationReport:
        """
        Execute all registered constraints against the provided context.
        Computes aggregated score and compiles violations.
        """
        start_time = time.perf_counter()
        violations: List[Violation] = []
        accumulated_penalty = 0.0

        for constraint in self.constraints:
            rule_violations = constraint.validate(context)
            if rule_violations:
                violations.extend(rule_violations)
                for v in rule_violations:
                    accumulated_penalty += v.penalty

                if self.strict_mode:
                    break

        latency_us = (time.perf_counter() - start_time) * 1_000_000.0
        final_score = max(0.0, 1.0 - accumulated_penalty)
        passed = (len(violations) == 0) and (final_score >= 0.70)

        return EvaluationReport(
            passed=passed,
            score=final_score,
            violations=violations,
            latency_us=latency_us,
            metadata={
                "constraint_count": len(self.constraints),
                "strict_mode": self.strict_mode,
                "language": context.language,
            },
        )
