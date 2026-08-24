from __future__ import annotations

from dataclasses import dataclass
import re

from app.engine.parser import ParseError, parse_expression

from .models import ITLTemplate


@dataclass(slots=True)
class Diagnostic:
    severity: str
    message: str
    object_name: str = ""


def point_usage(template: ITLTemplate, point_name: str) -> dict[str, list[str]]:
    folded = point_name.casefold()
    rules = [rule.name for rule in template.display_rules if any(name.casefold() == folded for name in rule.referenced_objects)]
    components = [component.name for component in template.components if any(name.casefold() == folded for name in component.vertices)]
    constraints: list[str] = []
    for point in template.points:
        for constraint in point.constraints:
            if constraint.parent.casefold() == folded or constraint.parent2.casefold() == folded:
                constraints.append(f"{point.name}: {constraint.type}")
    return {"Display Rules": rules, "Components": components, "Constraints": constraints}


def template_diagnostics(template: ITLTemplate) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    point_names = {point.name.casefold() for point in template.points}
    component_names = {component.name.casefold() for component in template.components}
    for rule in template.display_rules:
        expected = component_names if rule.rule_type == "Component Is Displayed" else point_names
        object_label = "component" if rule.rule_type == "Component Is Displayed" else "point"
        for name in rule.referenced_objects:
            if name.casefold() not in expected:
                diagnostics.append(Diagnostic("Warning", f"Rule references an unknown {object_label}: {name}", rule.name))
    for component in template.components:
        if not component.display_expression:
            continue
        if component.unresolved_expression:
            diagnostics.append(Diagnostic("Warning", f"Display expression contains unresolved text: {component.unresolved_expression}", component.name))
        expression = component.display_expression.strip()
        if re.search(r"\b(?:AND|OR|NOT)\s*$", expression, re.IGNORECASE) or re.match(r"^(?:AND|OR)\b", expression, re.IGNORECASE):
            diagnostics.append(Diagnostic("Error", "Display expression is incomplete in the source ITL", component.name))
        if component.rule_names:
            normalized = expression
            for index, name in enumerate(sorted(component.rule_names, key=len, reverse=True)):
                normalized = re.sub(re.escape(name), f"RULE_{index}", normalized, flags=re.IGNORECASE)
            try:
                parse_expression(normalized)
            except ParseError as error:
                diagnostics.append(Diagnostic("Warning", f"Display expression syntax could not be validated: {error.message}", component.name))
    return diagnostics
