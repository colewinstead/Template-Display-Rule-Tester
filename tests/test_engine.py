from __future__ import annotations

import unittest

from app.engine.ast_nodes import format_ast
from app.engine.evaluator import EvaluationError, evaluate_expression
from app.engine.parser import ParseError, parse_expression
from app.engine.rule_analyzer import compare_rules, conflict_scan, matrix, sweep, transitions, truth_table


class ExpressionEngineTests(unittest.TestCase):
    def assert_result(self, expression: str, expected: bool, **variables: object) -> None:
        self.assertEqual(evaluate_expression(expression, variables).value, expected)

    def test_comparison_operators(self) -> None:
        self.assert_result("GR_R < 1", True, GR_R=0)
        self.assert_result("GR_R <= 1", True, GR_R=1)
        self.assert_result("GR_R >= 1", True, GR_R=1)
        self.assert_result("GR_R = 1", True, GR_R=1)
        self.assert_result("GR_R == 1", True, GR_R=1.0)
        self.assert_result("GR_R != 1", True, GR_R=2)
        self.assert_result("GR_R <> 1", True, GR_R=2)

    def test_and_or_not_and_parentheses(self) -> None:
        values = {"GR_R": 0, "FIND_GR_R": 12, "SHOULDER_WIDTH": 8}
        self.assertTrue(evaluate_expression("GR_R < 1 AND FIND_GR_R > 0", values).value)
        self.assertTrue(evaluate_expression("GR_R < 1 OR FIND_GR_R < 0", values).value)
        self.assertFalse(evaluate_expression("NOT GR_R < 1", values).value)
        self.assertFalse(evaluate_expression("NOT (GR_R < 1)", values).value)
        self.assertTrue(evaluate_expression("(GR_R < 1 AND FIND_GR_R > 0) OR SHOULDER_WIDTH >= 8", values).value)

    def test_not_ast_interpretation_is_visible(self) -> None:
        ast = parse_expression("NOT GR_R < 1")
        self.assertEqual(format_ast(ast), "NOT\n└── <\n    ├── GR_R\n    └── 1")
        self.assertEqual(evaluate_expression("NOT GR_R < 1", {"GR_R": 1}).value, evaluate_expression("GR_R >= 1", {"GR_R": 1}).value)

    def test_case_insensitive_keywords_and_variables(self) -> None:
        self.assert_result("gr_r < 1 aNd find_gr_r > 0", True, GR_R=0, FIND_GR_R=2)

    def test_negative_decimal_zero_and_boolean(self) -> None:
        self.assert_result("DEPTH < -1.25", True, DEPTH=-2)
        self.assert_result("OFFSET = 0", True, OFFSET=0.0)
        self.assert_result("ACTIVE = TRUE AND NOT BLOCKED", True, ACTIVE=True, BLOCKED=False)

    def test_itl_helper_functions(self) -> None:
        values = {"A.X": 5, "B.X": 2, "A.Y": 1, "B.Y": 7}
        self.assert_result("HDIFF(A.X, B.X) > 2", True, **values)
        self.assert_result("AHDIFF(B.X, A.X) = 3", True, **values)
        self.assert_result("VDIFF(B.Y, A.Y) >= 6", True, **values)
        self.assert_result("AVDIFF(A.Y, B.Y) = 6", True, **values)
        self.assert_result("SLOPE(A.X, A.Y, B.X, B.Y) = -2", True, **values)

    def test_bracketed_bentley_point_name(self) -> None:
        self.assert_result("HDIFF([S/W Test.X], CG-BC.X) > 0", True, **{"S/W Test.X": 4, "CG-BC.X": 2})

    def test_explanation_contains_substitution_and_final_result(self) -> None:
        result = evaluate_expression("FIND_GR_R > 10 AND GR_R < 1", {"FIND_GR_R": 12, "GR_R": 0})
        self.assertIn("12 > 10", result.explanation)
        self.assertIn("0 < 1", result.explanation)
        self.assertIn("TRUE AND TRUE", result.explanation)
        self.assertTrue(result.explanation.endswith("FINAL RESULT: TRUE"))

    def test_unknown_variable_and_invalid_syntax(self) -> None:
        with self.assertRaisesRegex(EvaluationError, "Unknown variable: GR_RIGHT"):
            evaluate_expression("GR_RIGHT < 1", {"GR_R": 0})
        cases = {
            "GR_R <": "Missing value after '<'",
            "GR_R < 1 AND": "Missing condition after 'AND'",
            "(GR_R < 1": "Missing closing parenthesis",
        }
        for expression, message in cases.items():
            with self.subTest(expression=expression), self.assertRaisesRegex(ParseError, message):
                parse_expression(expression)

    def test_slope_zero_run_is_friendly_error(self) -> None:
        with self.assertRaisesRegex(EvaluationError, "horizontal run is zero"):
            evaluate_expression("SLOPE(A.X, A.Y, B.X, B.Y) > 0", {"A.X": 1, "A.Y": 0, "B.X": 1, "B.Y": 2})


class AnalyzerTests(unittest.TestCase):
    def test_range_and_transitions(self) -> None:
        rows = sweep("GR_R < 1", "GR_R", -1, 2, 1, {})
        self.assertEqual([row.result for row in rows], [True, True, False, False])
        self.assertEqual(transitions(rows), ["TRUE → FALSE at 1"])

    def test_matrix(self) -> None:
        result = matrix("A < 1 AND B > 0", "A", [0, 1], "B", [0, 5], {})
        self.assertEqual(result, [[False, True], [False, False]])

    def test_compare_and_conflicts(self) -> None:
        self.assertEqual(compare_rules("NOT X < 1", "X >= 1", "X", -10, 10, 1, {}), [])
        findings = conflict_scan([("A", "X <= 10"), ("B", "X >= 10")], "X", 9, 11, 1, {})
        self.assertIn((10, "OVERLAP", ["A", "B"]), findings)
        gap = conflict_scan([("A", "X < 10"), ("B", "X > 10")], "X", 10, 10, 1, {})
        self.assertEqual(gap, [(10, "GAP", [])])

    def test_truth_table(self) -> None:
        rows = truth_table("A AND NOT B")
        self.assertEqual(len(rows), 4)
        self.assertIn(({"A": True, "B": False}, True), rows)


if __name__ == "__main__":
    unittest.main()
