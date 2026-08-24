from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any


@dataclass(slots=True)
class ITLConstraint:
    type: str
    value: str = ""
    parent: str = ""
    parent2: str = ""
    equation: str = ""
    raw: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ITLPoint:
    name: str
    x: float | None
    y: float | None
    feature_name: str = ""
    style: str = ""
    constraints: list[ITLConstraint] = field(default_factory=list)
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def is_null(self) -> bool:
        text = f"{self.name} {self.style} {self.feature_name}".casefold()
        return "null" in text or self.raw.get("doNotConstruct", "").casefold() == "true"


@dataclass(slots=True)
class ITLDisplayRule:
    name: str
    rule_type: str
    point1: str = ""
    point2: str = ""
    test: str = ""
    value: float | None = None
    description: str = ""
    raw: dict[str, str] = field(default_factory=dict)
    used_by: list[str] = field(default_factory=list)

    @property
    def referenced_objects(self) -> list[str]:
        return [name for name in (self.point1, self.point2) if name]

    @property
    def tester_expression(self) -> str:
        def coordinate(name: str, axis: str) -> str:
            variable = f"{name}.{axis}"
            return variable if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.%\-]*", variable) else f"[{variable}]"

        if self.rule_type == "Component Is Displayed":
            displayed = coordinate(self.point1, "DISPLAYED")
            return f"{displayed} = TRUE"
        operator = {
            "LessThan": "<",
            "GreaterThan": ">",
            "LessThanOrEqual": "<=",
            "GreaterThanOrEqual": ">=",
            "Equal": "=",
            "NotEqual": "!=",
        }.get(self.test, self.test or "=")
        right = f"{self.value:.10g}" if self.value is not None else "0"
        if self.rule_type == "Horizontal Difference":
            left = f"HDIFF({coordinate(self.point1, 'X')}, {coordinate(self.point2, 'X')})"
        elif self.rule_type == "Absolute Horizontal Difference":
            left = f"AHDIFF({coordinate(self.point1, 'X')}, {coordinate(self.point2, 'X')})"
        elif self.rule_type == "Vertical Difference":
            left = f"VDIFF({coordinate(self.point1, 'Y')}, {coordinate(self.point2, 'Y')})"
        elif self.rule_type == "Absolute Vertical Difference":
            left = f"AVDIFF({coordinate(self.point1, 'Y')}, {coordinate(self.point2, 'Y')})"
        elif self.rule_type == "Slope":
            left = f"SLOPE({coordinate(self.point1, 'X')}, {coordinate(self.point1, 'Y')}, {coordinate(self.point2, 'X')}, {coordinate(self.point2, 'Y')})"
        else:
            left = f"{self.name}.VALUE"
        return f"{left} {operator} {right}"


@dataclass(slots=True)
class ITLComponent:
    name: str
    display_expression: str = ""
    rule_names: list[str] = field(default_factory=list)
    unresolved_expression: str = ""
    vertices: list[str] = field(default_factory=list)
    material: str = ""
    component_type: str = ""
    raw: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ITLTemplate:
    name: str
    category_path: tuple[str, ...]
    oid: str = ""
    description: str = ""
    points: list[ITLPoint] = field(default_factory=list)
    components: list[ITLComponent] = field(default_factory=list)
    display_rules: list[ITLDisplayRule] = field(default_factory=list)
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def path(self) -> str:
        return "/".join((*self.category_path, self.name))

    def point(self, name: str) -> ITLPoint | None:
        return next((point for point in self.points if point.name.casefold() == name.casefold()), None)

    def rule(self, name: str) -> ITLDisplayRule | None:
        return next((rule for rule in self.display_rules if rule.name.casefold() == name.casefold()), None)


@dataclass(slots=True)
class ITLLibrary:
    source_path: Path
    product_version: str
    linear_units: str
    angular_units: str
    metadata: dict[str, str]
    templates: list[ITLTemplate]
    tag_counts: dict[str, int]
    sha256: str = ""

    def template(self, path: str) -> ITLTemplate | None:
        folded = path.casefold()
        return next((template for template in self.templates if template.path.casefold() == folded), None)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "templates": len(self.templates),
            "points": sum(len(item.points) for item in self.templates),
            "components": sum(len(item.components) for item in self.templates),
            "display_rules": sum(len(item.display_rules) for item in self.templates),
            "constraints": sum(len(point.constraints) for item in self.templates for point in item.points),
        }


@dataclass(slots=True)
class ITLInspection:
    path: Path
    size: int
    sha256: str
    format: str
    root_tag: str
    parseable: bool
    error: str = ""
    tag_counts: dict[str, int] = field(default_factory=dict)
