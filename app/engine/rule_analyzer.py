from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable

from .evaluator import EvaluationError, evaluate_expression
from .parser import parse_expression


@dataclass(slots=True)
class RangeResult:
    value: float
    result: bool | None
    error: str = ""


def numeric_values(start: float, end: float, step: float, limit: int = 10_000) -> list[float]:
    if step == 0:
        raise ValueError("Step cannot be zero")
    if (end - start) * step < 0:
        raise ValueError("Step moves away from the end value")
    values: list[float] = []
    value = start
    epsilon = abs(step) * 1e-9
    while (value <= end + epsilon if step > 0 else value >= end - epsilon):
        values.append(round(value, 12))
        if len(values) >= limit:
            raise ValueError(f"Range exceeds the {limit:,}-row safety limit")
        value += step
    return values


def sweep(expression: str, variable: str, start: float, end: float, step: float, base: dict[str, Any]) -> list[RangeResult]:
    results: list[RangeResult] = []
    for value in numeric_values(start, end, step):
        values = dict(base)
        values[variable] = value
        try:
            result = evaluate_expression(expression, values).value
            results.append(RangeResult(value, result))
        except EvaluationError as error:
            results.append(RangeResult(value, None, str(error)))
    return results


def transitions(results: list[RangeResult]) -> list[str]:
    changes: list[str] = []
    for previous, current in zip(results, results[1:]):
        if previous.result is not None and current.result is not None and previous.result != current.result:
            changes.append(f"{str(previous.result).upper()} → {str(current.result).upper()} at {current.value:g}")
    return changes


def compare_rules(expression_a: str, expression_b: str, variable: str, start: float, end: float, step: float, base: dict[str, Any]) -> list[tuple[float, bool, bool]]:
    differences: list[tuple[float, bool, bool]] = []
    for value in numeric_values(start, end, step):
        values = dict(base)
        values[variable] = value
        a = evaluate_expression(expression_a, values).value
        b = evaluate_expression(expression_b, values).value
        if a != b:
            differences.append((value, a, b))
    return differences


def matrix(expression: str, variable_a: str, values_a: Iterable[float], variable_b: str, values_b: Iterable[float], base: dict[str, Any]) -> list[list[bool]]:
    columns = list(values_b)
    rows: list[list[bool]] = []
    for a in values_a:
        row: list[bool] = []
        for b in columns:
            values = dict(base)
            values[variable_a] = a
            values[variable_b] = b
            row.append(evaluate_expression(expression, values).value)
        rows.append(row)
    return rows


def conflict_scan(expressions: list[tuple[str, str]], variable: str, start: float, end: float, step: float, base: dict[str, Any]) -> list[tuple[float, str, list[str]]]:
    findings: list[tuple[float, str, list[str]]] = []
    for value in numeric_values(start, end, step):
        values = dict(base)
        values[variable] = value
        active = [name for name, expression in expressions if evaluate_expression(expression, values).value]
        if not active:
            findings.append((value, "GAP", []))
        elif len(active) > 1:
            findings.append((value, "OVERLAP", active))
    return findings


def truth_table(expression: str, variables: list[str] | None = None) -> list[tuple[dict[str, bool], bool]]:
    ast = parse_expression(expression)
    names = variables or sorted(ast.variables())
    if len(names) > 10:
        raise ValueError("Truth tables are limited to 10 variables")
    rows: list[tuple[dict[str, bool], bool]] = []
    for combination in product((False, True), repeat=len(names)):
        values = dict(zip(names, combination, strict=True))
        rows.append((values, evaluate_expression(expression, values).value))
    return rows
