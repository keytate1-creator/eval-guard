"""
Concrete constraint implementations for static code and text evaluation.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Sequence, Optional

from eval_guard.core import EvaluationContext, Violation
from eval_guard.ast_analyzer import (
    parse_safe_ast,
    ImportVisitor,
    McCabeComplexityVisitor,
    NestingDepthVisitor,
)


class BaseConstraint(ABC):
    """Abstract base class for all deterministic evaluation constraints."""

    def __init__(self, name: str, penalty: float = 0.25):
        self.name = name
        self.penalty = penalty

    @abstractmethod
    def validate(self, context: EvaluationContext) -> List[Violation]:
        """Evaluates the context and returns any discovered violations."""
        pass


class ValidPythonSyntaxConstraint(BaseConstraint):
    """Validates that the provided code conforms to standard Python syntax."""

    def __init__(self, penalty: float = 1.0):
        super().__init__(name="ValidPythonSyntax", penalty=penalty)

    def validate(self, context: EvaluationContext) -> List[Violation]:
        if context.language != "python":
            return []

        if context._cached_ast is None:
            context._cached_ast = parse_safe_ast(context.payload)

        ast_result = context._cached_ast
        if not ast_result.is_valid:
            return [
                Violation(
                    rule_name=self.name,
                    message=f"Failed syntax validation: {ast_result.error}",
                    severity="CRITICAL",
                    line_number=ast_result.error_line,
                    penalty=self.penalty,
                )
            ]
        return []


class ForbiddenImportsConstraint(BaseConstraint):
    """Enforces strict negative constraint prohibiting specific module imports."""

    def __init__(self, forbidden_modules: Sequence[str], penalty: float = 0.5):
        super().__init__(name="ForbiddenImports", penalty=penalty)
        self.forbidden_set = {mod.strip().lower() for mod in forbidden_modules}

    def validate(self, context: EvaluationContext) -> List[Violation]:
        if context.language != "python":
            return []

        if context._cached_ast is None:
            context._cached_ast = parse_safe_ast(context.payload)

        ast_result = context._cached_ast
        if not ast_result.is_valid:
            return []  # Syntax errors handled by ValidPythonSyntaxConstraint

        visitor = ImportVisitor()
        visitor.visit(ast_result.tree)

        violations: List[Violation] = []
        for module_name, lineno in visitor.imports:
            if module_name.lower() in self.forbidden_set:
                violations.append(
                    Violation(
                        rule_name=self.name,
                        message=f"Forbidden module import detected: '{module_name}'",
                        severity="ERROR",
                        line_number=lineno,
                        penalty=self.penalty,
                    )
                )
        return violations


class MaxCyclomaticComplexityConstraint(BaseConstraint):
    """Ensures no function exceeds the specified McCabe cyclomatic complexity."""

    def __init__(self, max_complexity: int = 10, penalty: float = 0.3):
        super().__init__(name="MaxCyclomaticComplexity", penalty=penalty)
        self.max_complexity = max_complexity

    def validate(self, context: EvaluationContext) -> List[Violation]:
        if context.language != "python":
            return []

        if context._cached_ast is None:
            context._cached_ast = parse_safe_ast(context.payload)

        ast_result = context._cached_ast
        if not ast_result.is_valid:
            return []

        visitor = McCabeComplexityVisitor()
        visitor.visit(ast_result.tree)

        violations: List[Violation] = []
        for func_name, (comp, lineno) in visitor.function_complexities.items():
            if comp > self.max_complexity:
                violations.append(
                    Violation(
                        rule_name=self.name,
                        message=(
                            f"Function '{func_name}' exceeds complexity limit "
                            f"(McCabe score: {comp}, maximum allowed: {self.max_complexity})"
                        ),
                        severity="WARNING",
                        line_number=lineno,
                        penalty=self.penalty,
                    )
                )
        return violations


class MaxNestingDepthConstraint(BaseConstraint):
    """Ensures control block nesting does not exceed the allowed maximum."""

    def __init__(self, max_depth: int = 4, penalty: float = 0.2):
        super().__init__(name="MaxNestingDepth", penalty=penalty)
        self.max_depth = max_depth

    def validate(self, context: EvaluationContext) -> List[Violation]:
        if context.language != "python":
            return []

        if context._cached_ast is None:
            context._cached_ast = parse_safe_ast(context.payload)

        ast_result = context._cached_ast
        if not ast_result.is_valid:
            return []

        visitor = NestingDepthVisitor()
        visitor.visit(ast_result.tree)

        if visitor.max_depth > self.max_depth:
            return [
                Violation(
                    rule_name=self.name,
                    message=(
                        f"Control structure nesting depth of {visitor.max_depth} "
                        f"exceeds limit of {self.max_depth}"
                    ),
                    severity="WARNING",
                    line_number=None,
                    penalty=self.penalty,
                )
            ]
        return []


class TokenBudgetConstraint(BaseConstraint):
    """Enforces explicit word/token minimum and maximum bounds."""

    def __init__(self, min_tokens: Optional[int] = None, max_tokens: Optional[int] = None, penalty: float = 0.25):
        super().__init__(name="TokenBudget", penalty=penalty)
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens

    def validate(self, context: EvaluationContext) -> List[Violation]:
        count = context.token_count
        violations: List[Violation] = []

        if self.min_tokens is not None and count < self.min_tokens:
            violations.append(
                Violation(
                    rule_name=self.name,
                    message=f"Payload token count {count} is below minimum requirement of {self.min_tokens}",
                    severity="ERROR",
                    line_number=None,
                    penalty=self.penalty,
                )
            )

        if self.max_tokens is not None and count > self.max_tokens:
            violations.append(
                Violation(
                    rule_name=self.name,
                    message=f"Payload token count {count} exceeds maximum allowed budget of {self.max_tokens}",
                    severity="ERROR",
                    line_number=None,
                    penalty=self.penalty,
                )
            )

        return violations


class RegexNegativeConstraint(BaseConstraint):
    """Flags matches of forbidden regular expression patterns in the payload."""

    def __init__(self, pattern: str, name: str = "RegexNegativeConstraint", penalty: float = 0.25):
        super().__init__(name=name, penalty=penalty)
        self.compiled_regex = re.compile(pattern, re.MULTILINE)

    def validate(self, context: EvaluationContext) -> List[Violation]:
        matches = list(self.compiled_regex.finditer(context.payload))
        violations: List[Violation] = []

        for match in matches:
            line_no = context.payload[:match.start()].count("\n") + 1
            matched_text = match.group(0)[:30]
            violations.append(
                Violation(
                    rule_name=self.name,
                    message=f"Prohibited pattern matched: '{matched_text}'",
                    severity="ERROR",
                    line_number=line_no,
                    penalty=self.penalty,
                )
            )
        return violations


class RegexPositiveConstraint(BaseConstraint):
    """Enforces that a mandatory regular expression pattern exists in the payload."""

    def __init__(self, pattern: str, name: str = "RegexPositiveConstraint", penalty: float = 0.3):
        super().__init__(name=name, penalty=penalty)
        self.compiled_regex = re.compile(pattern, re.MULTILINE)

    def validate(self, context: EvaluationContext) -> List[Violation]:
        if not self.compiled_regex.search(context.payload):
            return [
                Violation(
                    rule_name=self.name,
                    message=f"Mandatory required pattern '{self.compiled_regex.pattern}' was not found in payload",
                    severity="ERROR",
                    line_number=None,
                    penalty=self.penalty,
                )
            ]
        return []
