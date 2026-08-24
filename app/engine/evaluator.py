from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose
from typing import Any, Callable

from .ast_nodes import ASTNode, Comparison, FunctionCall, Literal, Logical, Not, Variable, format_ast
from .parser import parse_expression


class EvaluationError(ValueError):
    pass


def _display(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


@dataclass(slots=True)
class Trace:
    expression: str
    value: Any
    substituted: str = ""
    children: list[Trace] = field(default_factory=list)

    def explanation_lines(self) -> list[str]:
        lines: list[str] = []
        for child in self.children:
            lines.extend(child.explanation_lines())
        if self.children:
            lines.append(self.expression)
            if self.substituted and self.substituted != self.expression:
                lines.append(self.substituted)
            lines.append(_display(self.value))
            lines.append("")
        return lines


@dataclass(slots=True)
class EvaluationResult:
    value: bool
    raw_value: Any
    ast: ASTNode
    trace: Trace

    @property
    def ast_text(self) -> str:
        return format_ast(self.ast)

    @property
    def variables(self) -> set[str]:
        return self.ast.variables()

    @property
    def explanation(self) -> str:
        lines = self.trace.explanation_lines()
        lines.extend([f"FINAL RESULT: {_display(self.value)}"])
        return "\n".join(lines)


def _compare(left: Any, operator: str, right: Any) -> bool:
    if operator in {"=", "=="}:
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
        return left == right
    if operator in {"!=", "<>"}:
        return not _compare(left, "=", right)
    if isinstance(left, bool) or isinstance(right, bool):
        raise EvaluationError(f"Operator '{operator}' cannot order Boolean values")
    try:
        if operator == "<":
            return left < right
        if operator == ">":
            return left > right
        if operator == "<=":
            return left <= right
        if operator == ">=":
            return left >= right
    except TypeError as error:
        raise EvaluationError(f"Cannot compare {_display(left)} and {_display(right)}") from error
    raise EvaluationError(f"Unsupported comparison operator '{operator}'")


def _hdiff(first: float, second: float) -> float:
    return float(first) - float(second)


def _vdiff(first: float, second: float) -> float:
    return float(first) - float(second)


def _slope(x1: float, y1: float, x2: float, y2: float) -> float:
    run = float(x2) - float(x1)
    if isclose(run, 0.0, abs_tol=1e-15):
        raise EvaluationError("SLOPE is undefined because the horizontal run is zero")
    return (float(y2) - float(y1)) / run


FUNCTIONS: dict[str, tuple[int, Callable[..., Any]]] = {
    "HDIFF": (2, _hdiff),
    "AHDIFF": (2, lambda a, b: abs(_hdiff(a, b))),
    "VDIFF": (2, _vdiff),
    "AVDIFF": (2, lambda a, b: abs(_vdiff(a, b))),
    "SLOPE": (4, _slope),
    "ABS": (1, abs),
}


def _evaluate(node: ASTNode, variables: dict[str, Any]) -> tuple[Any, Trace]:
    if isinstance(node, Literal):
        return node.value, Trace(_display(node.value), node.value)
    if isinstance(node, Variable):
        if node.name in variables:
            value = variables[node.name]
        else:
            match = next((value for name, value in variables.items() if name.casefold() == node.name.casefold()), None)
            if match is None and not any(name.casefold() == node.name.casefold() for name in variables):
                raise EvaluationError(f"Unknown variable: {node.name}")
            value = match
        return value, Trace(node.name, value, f"{node.name} = {_display(value)}")
    if isinstance(node, FunctionCall):
        name = node.name.upper()
        if name not in FUNCTIONS:
            raise EvaluationError(f"Unknown function: {node.name}")
        expected, function = FUNCTIONS[name]
        if len(node.arguments) != expected:
            raise EvaluationError(f"{name} expects {expected} arguments, received {len(node.arguments)}")
        evaluated = [_evaluate(argument, variables) for argument in node.arguments]
        values = [item[0] for item in evaluated]
        try:
            value = function(*values)
        except EvaluationError:
            raise
        except (TypeError, ValueError, ZeroDivisionError) as error:
            raise EvaluationError(f"{name} could not evaluate its inputs") from error
        expression = f"{name}({', '.join(child.expression for _, child in evaluated)})"
        substituted = f"{name}({', '.join(_display(value) for value in values)}) = {_display(value)}"
        return value, Trace(expression, value, substituted, [child for _, child in evaluated])
    if isinstance(node, Comparison):
        left, left_trace = _evaluate(node.left, variables)
        right, right_trace = _evaluate(node.right, variables)
        result = _compare(left, node.operator, right)
        expression = f"{left_trace.expression} {node.operator} {right_trace.expression}"
        substituted = f"{_display(left)} {node.operator} {_display(right)}"
        return result, Trace(expression, result, substituted, [left_trace, right_trace])
    if isinstance(node, Not):
        value, child = _evaluate(node.operand, variables)
        if not isinstance(value, bool):
            raise EvaluationError("NOT requires a Boolean condition")
        result = not value
        return result, Trace(f"NOT {child.expression}", result, f"NOT {_display(value)}", [child])
    if isinstance(node, Logical):
        left, left_trace = _evaluate(node.left, variables)
        right, right_trace = _evaluate(node.right, variables)
        if not isinstance(left, bool) or not isinstance(right, bool):
            raise EvaluationError(f"{node.operator} requires Boolean conditions")
        result = left and right if node.operator == "AND" else left or right
        expression = f"{left_trace.expression} {node.operator} {right_trace.expression}"
        substituted = f"{_display(left)} {node.operator} {_display(right)}"
        return result, Trace(expression, result, substituted, [left_trace, right_trace])
    raise EvaluationError(f"Unsupported expression node: {type(node).__name__}")


def evaluate_ast(ast: ASTNode, variables: dict[str, Any]) -> EvaluationResult:
    raw_value, trace = _evaluate(ast, variables)
    if not isinstance(raw_value, bool):
        raise EvaluationError("The expression must produce TRUE or FALSE")
    return EvaluationResult(raw_value, raw_value, ast, trace)


def evaluate_expression(expression: str, variables: dict[str, Any]) -> EvaluationResult:
    return evaluate_ast(parse_expression(expression), variables)
