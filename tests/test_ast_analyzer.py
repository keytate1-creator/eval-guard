"""
Unit tests for the AST static analyzer using standard library unittest.
"""

import ast
import unittest
from eval_guard.ast_analyzer import (
    parse_safe_ast,
    ImportVisitor,
    McCabeComplexityVisitor,
    NestingDepthVisitor,
)


class TestASTAnalyzer(unittest.TestCase):

    def test_parse_safe_ast_valid(self):
        code = "def add(a, b):\n    return a + b\n"
        res = parse_safe_ast(code)
        self.assertTrue(res.is_valid)
        self.assertIsNone(res.error)
        self.assertIsInstance(res.tree, ast.AST)

    def test_parse_safe_ast_syntax_error(self):
        code = "def bad_syntax(:\n    pass\n"
        res = parse_safe_ast(code)
        self.assertFalse(res.is_valid)
        self.assertIn("SyntaxError", res.error)
        self.assertEqual(res.error_line, 1)

    def test_import_visitor(self):
        code = """
import os
import sys as system
from math import sqrt, pi
from collections.abc import Mapping
"""
        res = parse_safe_ast(code)
        visitor = ImportVisitor()
        visitor.visit(res.tree)

        modules = [m[0] for m in visitor.imports]
        self.assertIn("os", modules)
        self.assertIn("sys", modules)
        self.assertIn("math", modules)
        self.assertIn("collections", modules)

    def test_mccabe_complexity_simple(self):
        code = """
def linear_function(x):
    y = x + 1
    return y * 2
"""
        res = parse_safe_ast(code)
        visitor = McCabeComplexityVisitor()
        visitor.visit(res.tree)

        self.assertIn("linear_function", visitor.function_complexities)
        comp, line = visitor.function_complexities["linear_function"]
        self.assertEqual(comp, 1)
        self.assertEqual(line, 2)

    def test_mccabe_complexity_branches(self):
        code = """
def branching_function(x, y):
    if x > 0 and y > 0:
        for i in range(x):
            if i % 2 == 0:
                pass
    elif x < 0:
        while y > 0:
            y -= 1
    return x + y
"""
        res = parse_safe_ast(code)
        visitor = McCabeComplexityVisitor()
        visitor.visit(res.tree)

        comp, _ = visitor.function_complexities["branching_function"]
        self.assertEqual(comp, 7)

    def test_nesting_depth_visitor(self):
        code = """
def deep_nesting():
    if True:
        for i in range(10):
            while True:
                with open("file.txt"):
                    pass
"""
        res = parse_safe_ast(code)
        visitor = NestingDepthVisitor()
        visitor.visit(res.tree)

        self.assertEqual(visitor.max_depth, 4)


if __name__ == "__main__":
    unittest.main()
