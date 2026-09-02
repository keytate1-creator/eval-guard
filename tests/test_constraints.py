"""
Unit tests for deterministic constraints using standard library unittest.
"""

import unittest
from eval_guard.core import EvaluationContext
from eval_guard.constraints import (
    ValidPythonSyntaxConstraint,
    ForbiddenImportsConstraint,
    MaxCyclomaticComplexityConstraint,
    MaxNestingDepthConstraint,
    TokenBudgetConstraint,
    RegexNegativeConstraint,
    RegexPositiveConstraint,
)


class TestConstraints(unittest.TestCase):

    def test_syntax_constraint(self):
        constraint = ValidPythonSyntaxConstraint()
        valid_ctx = EvaluationContext("x = 42")
        self.assertEqual(len(constraint.validate(valid_ctx)), 0)

        invalid_ctx = EvaluationContext("def bad(")
        violations = constraint.validate(invalid_ctx)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].severity, "CRITICAL")

    def test_forbidden_imports_constraint(self):
        constraint = ForbiddenImportsConstraint(["os", "subprocess"])

        clean_ctx = EvaluationContext("import math\nfrom json import loads")
        self.assertEqual(len(constraint.validate(clean_ctx)), 0)

        dirty_ctx = EvaluationContext("import os\nfrom subprocess import Popen")
        violations = constraint.validate(dirty_ctx)
        self.assertEqual(len(violations), 2)
        self.assertTrue(any("os" in v.message for v in violations))
        self.assertTrue(any("subprocess" in v.message for v in violations))

    def test_token_budget_constraint(self):
        constraint = TokenBudgetConstraint(min_tokens=3, max_tokens=6)

        # 4 tokens: valid
        ctx_valid = EvaluationContext("one two three four")
        self.assertEqual(len(constraint.validate(ctx_valid)), 0)

        # 2 tokens: too short
        ctx_short = EvaluationContext("one two")
        violations_short = constraint.validate(ctx_short)
        self.assertEqual(len(violations_short), 1)
        self.assertIn("below minimum", violations_short[0].message)

        # 7 tokens: too long
        ctx_long = EvaluationContext("one two three four five six seven")
        violations_long = constraint.validate(ctx_long)
        self.assertEqual(len(violations_long), 1)
        self.assertIn("exceeds maximum", violations_long[0].message)

    def test_regex_constraints(self):
        neg_constraint = RegexNegativeConstraint(r"\bTODO\b")
        clean_ctx = EvaluationContext("print('Finished implementation')")
        self.assertEqual(len(neg_constraint.validate(clean_ctx)), 0)

        dirty_ctx = EvaluationContext("# TODO: fix this bug later\nprint('incomplete')")
        violations = neg_constraint.validate(dirty_ctx)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].line_number, 1)

        pos_constraint = RegexPositiveConstraint(r"->\s*\w+", name="ReturnTypeAnnotated")
        annotated_ctx = EvaluationContext("def compute() -> int:\n    return 1")
        self.assertEqual(len(pos_constraint.validate(annotated_ctx)), 0)

        unannotated_ctx = EvaluationContext("def compute():\n    return 1")
        self.assertEqual(len(pos_constraint.validate(unannotated_ctx)), 1)


if __name__ == "__main__":
    unittest.main()
