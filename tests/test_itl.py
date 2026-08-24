from __future__ import annotations

from pathlib import Path
import unittest

from app.itl.analyzer import point_usage, template_diagnostics
from app.itl.importer import import_rule
from app.itl.parser import inspect_itl, parse_itl


SAMPLE = Path(__file__).resolve().parents[1] / "rwd.itl"


@unittest.skipUnless(SAMPLE.is_file(), "Included rwd.itl fixture is unavailable")
class RealITLParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.library = parse_itl(SAMPLE)

    def test_sample_detection_and_integrity(self) -> None:
        inspection = inspect_itl(SAMPLE)
        self.assertTrue(inspection.parseable)
        self.assertEqual(inspection.format, "XML")
        self.assertEqual(inspection.root_tag, "InRoads")
        self.assertEqual(inspection.sha256.upper(), "93EEE35AF190F4A1323EF77EAAE5C4C7B5EEB949CB765DCF62282C068E9DE26F")

    def test_real_counts(self) -> None:
        self.assertEqual(self.library.counts["templates"], 216)
        self.assertEqual(self.library.counts["points"], 5889)
        self.assertEqual(self.library.counts["components"], 2921)
        self.assertEqual(self.library.counts["display_rules"], 1027)
        self.assertEqual(self.library.counts["constraints"], 11778)

    def test_templates_points_components_and_rules_discovered(self) -> None:
        template = self.library.template("MDOT/Components/Guardrail/Guardrail On Shoulder")
        self.assertIsNotNone(template)
        assert template is not None
        self.assertIsNotNone(template.point("GR10"))
        self.assertTrue(any(component.name == "GRX" for component in template.components))
        self.assertIsNotNone(template.rule("GuardrailFindInsideShoulder"))

    def test_rule_component_association_and_import(self) -> None:
        template = self.library.template("MDOT/Components/Guardrail/Guardrail On Shoulder")
        assert template is not None
        rule = template.rule("GuardrailFindInsideShoulder")
        assert rule is not None
        self.assertIn("GRX", rule.used_by)
        tester_rule, variables = import_rule(template, rule)
        self.assertEqual(tester_rule.expression, "HDIFF(GR10.X, ES.X) < 0")
        self.assertEqual({variable.name for variable in variables}, {"GR10.X", "ES.X"})

    def test_point_usage_uses_actual_relationships(self) -> None:
        template = self.library.template("MDOT/Components/Guardrail/Guardrail On Shoulder")
        assert template is not None
        usage = point_usage(template, "GR10")
        self.assertIn("GuardrailFindInsideShoulder", usage["Display Rules"])

    def test_malformed_source_expression_is_diagnostic_not_guess(self) -> None:
        template = self.library.template("MDOT/Components/Pavement/New Construction")
        assert template is not None
        findings = template_diagnostics(template)
        self.assertTrue(any(item.object_name == "SUBGRADE" and "incomplete" in item.message for item in findings))

    def test_every_real_atomic_rule_generates_parseable_tester_expression(self) -> None:
        from app.engine.parser import parse_expression

        for template in self.library.templates:
            for rule in template.display_rules:
                with self.subTest(template=template.path, rule=rule.name):
                    parse_expression(rule.tester_expression)


if __name__ == "__main__":
    unittest.main()
