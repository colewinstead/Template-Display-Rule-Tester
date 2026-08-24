from __future__ import annotations

from app.models.project import RuleModel, VariableModel

from .models import ITLDisplayRule, ITLTemplate


def import_rule(template: ITLTemplate, itl_rule: ITLDisplayRule) -> tuple[RuleModel, list[VariableModel]]:
    variables: list[VariableModel] = []
    if itl_rule.rule_type == "Component Is Displayed":
        variables.append(VariableModel(f"{itl_rule.point1}.DISPLAYED", False, "Boolean", "ITL test value", "Tester state for referenced component"))
    else:
        for point_name in itl_rule.referenced_objects:
            point = template.point(point_name)
            x = point.x if point and point.x is not None else 0.0
            y = point.y if point and point.y is not None else 0.0
            if itl_rule.rule_type in {"Horizontal Difference", "Absolute Horizontal Difference", "Slope"}:
                variables.append(VariableModel(f"{point_name}.X", x, "Number", "ITL test value", f"Test horizontal coordinate for {point_name}"))
            if itl_rule.rule_type in {"Vertical Difference", "Absolute Vertical Difference", "Slope"}:
                variables.append(VariableModel(f"{point_name}.Y", y, "Number", "ITL test value", f"Test vertical coordinate for {point_name}"))
    rule = RuleModel(
        name=itl_rule.name,
        expression=itl_rule.tester_expression,
        source="ITL",
        description=itl_rule.description,
        enabled=True,
        itl_template=template.path,
        itl_rule_name=itl_rule.name,
        controlled_components=list(itl_rule.used_by),
        original=dict(itl_rule.raw),
    )
    return rule, variables
