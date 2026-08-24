from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .models import (
    ITLComponent,
    ITLConstraint,
    ITLDisplayRule,
    ITLInspection,
    ITLLibrary,
    ITLPoint,
    ITLTemplate,
)
from .reader import detect_format, file_sha256, validate_readable_itl


class ITLParseError(ValueError):
    pass


def _float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def inspect_itl(path: str | Path) -> ITLInspection:
    source = validate_readable_itl(path)
    file_format = detect_format(source)
    digest = file_sha256(source)
    if file_format != "XML":
        return ITLInspection(source, source.stat().st_size, digest, file_format, "", False, "This parser currently supports XML ITL libraries.")
    counts: Counter[str] = Counter()
    root_tag = ""
    try:
        for event, element in ET.iterparse(source, events=("start",)):
            tag = element.tag.split("}")[-1]
            root_tag = root_tag or tag
            counts[tag] += 1
    except (ET.ParseError, OSError) as error:
        return ITLInspection(source, source.stat().st_size, digest, file_format, root_tag, False, str(error), dict(counts))
    return ITLInspection(source, source.stat().st_size, digest, file_format, root_tag, True, tag_counts=dict(counts))


def _extract_rule_names(expression: str, names: list[str]) -> tuple[list[str], str]:
    if not expression.strip():
        return [], ""
    candidates: list[tuple[int, int, str]] = []
    for name in sorted(set(names), key=len, reverse=True):
        if not name:
            continue
        pattern = re.compile(rf"(?<![A-Za-z0-9_.%\-]){re.escape(name)}(?![A-Za-z0-9_.%\-])", re.IGNORECASE)
        candidates.extend((match.start(), match.end(), name) for match in pattern.finditer(expression))
    selected: list[tuple[int, int, str]] = []
    for candidate in sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0]))):
        if not any(candidate[0] < end and candidate[1] > start for start, end, _ in selected):
            selected.append(candidate)
    selected.sort()
    rule_names = list(dict.fromkeys(item[2] for item in selected))
    masked = list(expression)
    for start, end, _ in selected:
        masked[start:end] = " " * (end - start)
    remainder = "".join(masked)
    remainder = re.sub(r"\b(?:AND|OR|NOT|TRUE|FALSE)\b|[()]", " ", remainder, flags=re.IGNORECASE)
    unresolved = " ".join(remainder.split())
    return rule_names, unresolved


def _parse_template(element: ET.Element, category_path: tuple[str, ...]) -> ITLTemplate:
    template = ITLTemplate(
        name=element.get("name", "(unnamed template)"),
        category_path=category_path,
        oid=element.get("oid", ""),
        description=element.get("description", ""),
        raw=dict(element.attrib),
    )
    points = element.find("Points")
    if points is not None:
        for point_element in points.findall("Point"):
            constraints = [
                ITLConstraint(
                    type=item.get("type", ""),
                    value=item.get("value", ""),
                    parent=item.get("parent", ""),
                    parent2=item.get("parent2", ""),
                    equation=item.get("equation", ""),
                    raw=dict(item.attrib),
                )
                for item in point_element.findall("Constraint")
            ]
            template.points.append(
                ITLPoint(
                    name=point_element.get("name", "(unnamed point)"),
                    x=_float(point_element.get("x")),
                    y=_float(point_element.get("y")),
                    feature_name=point_element.get("featureName", ""),
                    style=point_element.get("style", ""),
                    constraints=constraints,
                    raw=dict(point_element.attrib),
                )
            )
    rules_element = element.find("DisplayRules")
    if rules_element is not None:
        for rule_element in rules_element.findall("DisplayRule"):
            template.display_rules.append(
                ITLDisplayRule(
                    name=rule_element.get("name", "(unnamed rule)"),
                    description=rule_element.get("description", ""),
                    rule_type=rule_element.get("type", ""),
                    point1=rule_element.get("point1", ""),
                    point2=rule_element.get("point2", ""),
                    test=rule_element.get("test", ""),
                    value=_float(rule_element.get("value")),
                    raw=dict(rule_element.attrib),
                )
            )
    rule_names = [rule.name for rule in template.display_rules]
    components = element.find("Components")
    if components is not None:
        for component_element in components.findall("Component"):
            expression = component_element.get("displayExpression", "").strip()
            referenced, unresolved = _extract_rule_names(expression, rule_names)
            component = ITLComponent(
                name=component_element.get("name", "(unnamed component)"),
                display_expression=expression,
                rule_names=referenced,
                unresolved_expression=unresolved,
                vertices=[vertex.get("pointName", vertex.get("name", "")) for vertex in component_element.findall("Vertex")],
                material=component_element.get("material", ""),
                component_type=component_element.get("type", ""),
                raw=dict(component_element.attrib),
            )
            template.components.append(component)
            for rule_name in referenced:
                rule = template.rule(rule_name)
                if rule and component.name not in rule.used_by:
                    rule.used_by.append(component.name)
    return template


def parse_itl(path: str | Path) -> ITLLibrary:
    inspection = inspect_itl(path)
    if not inspection.parseable:
        raise ITLParseError(f"Cannot parse ITL: {inspection.error or inspection.format}")
    try:
        root = ET.parse(inspection.path).getroot()
    except (ET.ParseError, OSError) as error:
        raise ITLParseError(f"Cannot parse ITL XML: {error}") from error
    library_element = root.find("TemplateLibrary")
    if library_element is None:
        raise ITLParseError("XML does not contain an InRoads TemplateLibrary element")
    templates: list[ITLTemplate] = []

    def visit_category(category: ET.Element, path_parts: tuple[str, ...]) -> None:
        name = category.get("name", "")
        next_path = path_parts + ((name,) if name else ())
        for template_element in category.findall("Template"):
            templates.append(_parse_template(template_element, next_path))
        for child in category.findall("Category"):
            visit_category(child, next_path)

    for category in library_element.findall("Category"):
        visit_category(category, ())
    return ITLLibrary(
        source_path=inspection.path,
        product_version=root.get("productVersion", ""),
        linear_units=root.get("linearUnits", ""),
        angular_units=root.get("angularUnits", ""),
        metadata=dict(library_element.attrib),
        templates=templates,
        tag_counts=inspection.tag_counts,
        sha256=inspection.sha256,
    )
