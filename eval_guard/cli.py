"""
Command-line interface for the EvalGuard deterministic evaluation engine.
"""

from __future__ import annotations

import sys
import os
import argparse
from typing import Sequence, Optional

from eval_guard.core import RuleEngine, EvaluationContext
from eval_guard.constraints import (
    ValidPythonSyntaxConstraint,
    ForbiddenImportsConstraint,
    MaxCyclomaticComplexityConstraint,
    MaxNestingDepthConstraint,
    TokenBudgetConstraint,
    RegexNegativeConstraint,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval-guard",
        description="Deterministic High-Throughput Constraint & AST Evaluation Engine for LLM Outputs.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: run
    run_parser = subparsers.add_parser("run", help="Run static evaluations on input code or text.")
    run_parser.add_argument(
        "-i", "--input",
        dest="input_source",
        required=True,
        help="Path to file to evaluate, or raw string if prefixed with 'raw:'",
    )
    run_parser.add_argument(
        "-l", "--language",
        default="python",
        help="Language mode (default: python)",
    )
    run_parser.add_argument(
        "--strict",
        action="store_true",
        help="Halt evaluation immediately upon encountering the first violation.",
    )
    run_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output report format (default: text)",
    )
    run_parser.add_argument(
        "--output",
        help="Optional path to write the evaluation report.",
    )
    run_parser.add_argument(
        "--max-complexity",
        type=int,
        default=10,
        help="Maximum allowable McCabe cyclomatic complexity (default: 10)",
    )
    run_parser.add_argument(
        "--forbidden-imports",
        help="Comma-separated list of prohibited modules (e.g., 'os,sys,subprocess')",
    )

    return parser


def load_payload(source: str) -> str:
    """Loads source payload from file or inline string."""
    if source.startswith("raw:"):
        return source[4:]

    if not os.path.exists(source):
        raise FileNotFoundError(f"Input file not found: {source}")

    with open(source, "r", encoding="utf-8") as f:
        return f.read()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            payload = load_payload(args.input_source)
        except Exception as e:
            sys.stderr.write(f"Error loading input: {e}\n")
            return 2

        engine = RuleEngine(strict_mode=args.strict)

        # Register standard suite
        engine.add_constraint(ValidPythonSyntaxConstraint(penalty=1.0))
        engine.add_constraint(MaxCyclomaticComplexityConstraint(max_complexity=args.max_complexity))
        engine.add_constraint(MaxNestingDepthConstraint(max_depth=5))
        engine.add_constraint(RegexNegativeConstraint(r"\bTODO\b|\bFIXME\b", name="NoPlaceholders"))

        if args.forbidden_imports:
            forbidden = [m.strip() for m in args.forbidden_imports.split(",") if m.strip()]
            engine.add_constraint(ForbiddenImportsConstraint(forbidden_modules=forbidden))

        context = EvaluationContext(payload=payload, language=args.language)
        report = engine.evaluate(context)

        output_content = ""
        if args.format == "json":
            output_content = report.to_json(indent=2)
        else:
            lines = [
                "==================================================",
                f" EVALUATION REPORT (Latency: {report.latency_us:.1f} µs)",
                "==================================================",
                f" Status : {'PASSED' if report.passed else 'FAILED'}",
                f" Score  : {report.score:.2f} / 1.00",
                f" Errors : {len(report.violations)} violation(s)",
            ]
            if report.violations:
                lines.append("--------------------------------------------------")
                for idx, v in enumerate(report.violations, 1):
                    loc = f" [Line {v.line_number}]" if v.line_number else ""
                    lines.append(f" {idx}. [{v.severity}] {v.rule_name}{loc}: {v.message}")
            lines.append("==================================================")
            output_content = "\n".join(lines)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as out_file:
                out_file.write(output_content + "\n")
        else:
            print(output_content)

        return 0 if report.passed else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
