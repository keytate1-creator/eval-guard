"""
Integration tests for the RuleEngine orchestration and scoring using standard library unittest.
"""

import unittest
from eval_guard.core import RuleEngine, EvaluationContext
from eval_guard.constraints import (
    ValidPythonSyntaxConstraint,
    ForbiddenImportsConstraint,
    MaxCyclomaticComplexityConstraint,
)


class TestRuleEngine(unittest.TestCase):

    def test_rule_engine_full_pass(self):
        engine = RuleEngine()
        engine.add_constraint(ValidPythonSyntaxConstraint())
        engine.add_constraint(ForbiddenImportsConstraint(["sys", "os"]))
        engine.add_constraint(MaxCyclomaticComplexityConstraint(max_complexity=5))

        clean_code = """
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
"""
        context = EvaluationContext(clean_code)
        report = engine.evaluate(context)

        self.assertTrue(report.passed)
        self.assertEqual(report.score, 1.0)
        self.assertEqual(len(report.violations), 0)
        self.assertGreater(report.latency_us, 0.0)

    def test_rule_engine_violations_and_penalty(self):
        engine = RuleEngine()
        engine.add_constraint(ForbiddenImportsConstraint(["os"], penalty=0.5))
        engine.add_constraint(MaxCyclomaticComplexityConstraint(max_complexity=2, penalty=0.3))

        code = """
import os

def complex_func(a, b, c):
    if a:
        if b:
            if c:
                return 1
    return 0
"""
        context = EvaluationContext(code)
        report = engine.evaluate(context)

        self.assertFalse(report.passed)
        # Violations: 1 for 'os' (penalty 0.5) + 1 for complexity (score 4 > 2, penalty 0.3)
        self.assertEqual(len(report.violations), 2)
        self.assertAlmostEqual(report.score, 0.2, places=4)

    def test_rule_engine_strict_mode(self):
        engine = RuleEngine(strict_mode=True)
        engine.add_constraint(ForbiddenImportsConstraint(["os"], penalty=0.4))
        engine.add_constraint(ForbiddenImportsConstraint(["sys"], penalty=0.4))

        code = "import os\nimport sys"
        context = EvaluationContext(code)
        report = engine.evaluate(context)

        # In strict mode, halts after the first violation
        self.assertEqual(len(report.violations), 1)
        self.assertAlmostEqual(report.score, 0.6, places=4)


if __name__ == "__main__":
    unittest.main()
