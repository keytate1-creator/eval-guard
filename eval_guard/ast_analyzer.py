"""
Abstract Syntax Tree (AST) static analyzer for EvalGuard.
Safely analyzes Python code structure, complexity, and imports without code execution.
"""

from __future__ import annotations

import ast
from typing import List, Dict, Tuple, Optional


class SafeASTParseResult:
    """Wrapper holding parsed AST or syntax error metadata."""
    def __init__(self, tree: Optional[ast.AST], error: Optional[str] = None, error_line: Optional[int] = None):
        self.tree = tree
        self.error = error
        self.error_line = error_line

    @property
    def is_valid(self) -> bool:
        return self.tree is not None and self.error is None


def parse_safe_ast(source_code: str) -> SafeASTParseResult:
    """
    Parses source code into an AST safely.
    Catches SyntaxError, IndentationError, and MemoryError.
    """
    try:
        tree = ast.parse(source_code)
        return SafeASTParseResult(tree=tree)
    except SyntaxError as err:
        return SafeASTParseResult(
            tree=None,
            error=f"SyntaxError: {err.msg}",
            error_line=err.lineno,
        )
    except Exception as err:
        return SafeASTParseResult(
            tree=None,
            error=f"ASTParseError: {str(err)}",
            error_line=None,
        )


class ImportVisitor(ast.NodeVisitor):
    """Gathers all imported module names and specific imported attributes."""

    def __init__(self) -> None:
        self.imports: List[Tuple[str, int]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            self.imports.append((base_module, node.lineno))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split(".")[0]
            self.imports.append((base_module, node.lineno))
        self.generic_visit(node)


class McCabeComplexityVisitor(ast.NodeVisitor):
    """
    Calculates McCabe Cyclomatic Complexity per function/method.
    Base complexity is 1. Each decision branch increases complexity by 1:
    - If, While, For, AsyncFor
    - ExceptHandler, With, AsyncWith
    - Assert, Comprehension (if conditions)
    - BoolOp (and/or operands)
    """

    def __init__(self) -> None:
        self.function_complexities: Dict[str, Tuple[int, int]] = {}
        self._current_function: Optional[str] = None
        self._current_complexity: int = 1
        self._current_lineno: int = 1

    def _enter_function(self, name: str, lineno: int) -> None:
        self._current_function = name
        self._current_complexity = 1
        self._current_lineno = lineno

    def _exit_function(self) -> None:
        if self._current_function:
            self.function_complexities[self._current_function] = (
                self._current_complexity,
                self._current_lineno,
            )
            self._current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        parent_func = self._current_function
        parent_comp = self._current_complexity
        parent_line = self._current_lineno

        self._enter_function(node.name, node.lineno)
        self.generic_visit(node)
        self._exit_function()

        self._current_function = parent_func
        self._current_complexity = parent_comp
        self._current_lineno = parent_line

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        parent_func = self._current_function
        parent_comp = self._current_complexity
        parent_line = self._current_lineno

        self._enter_function(node.name, node.lineno)
        self.generic_visit(node)
        self._exit_function()

        self._current_function = parent_func
        self._current_complexity = parent_comp
        self._current_lineno = parent_line

    def _increment(self, amount: int = 1) -> None:
        if self._current_function:
            self._current_complexity += amount

    def visit_If(self, node: ast.If) -> None:
        self._increment(1)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._increment(1)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._increment(1)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._increment(1)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._increment(1)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self._increment(1)
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Every extra condition in an 'and' / 'or' expression introduces a branch
        self._increment(len(node.values) - 1)
        self.generic_visit(node)


class NestingDepthVisitor(ast.NodeVisitor):
    """Calculates the maximum control structure nesting depth in the AST."""

    NESTING_NODES = (
        ast.If,
        ast.For,
        ast.While,
        ast.AsyncFor,
        ast.With,
        ast.AsyncWith,
        ast.Try,
    )

    def __init__(self) -> None:
        self.max_depth: int = 0
        self._current_depth: int = 0

    def generic_visit(self, node: ast.AST) -> None:
        is_nesting = isinstance(node, self.NESTING_NODES)
        if is_nesting:
            self._current_depth += 1
            if self._current_depth > self.max_depth:
                self.max_depth = self._current_depth

        super().generic_visit(node)

        if is_nesting:
            self._current_depth -= 1
