from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class VariableModel:
    name: str
    value: float | bool | str = 0.0
    value_type: str = "Number"
    source: str = "Manual"
    description: str = ""
    minimum: float = -50.0
    maximum: float = 50.0
    step: float = 0.5

    def typed_value(self) -> Any:
        if self.value_type == "Boolean":
            if isinstance(self.value, str):
                return self.value.strip().casefold() in {"true", "1", "yes", "on"}
            return bool(self.value)
        if self.value_type == "Number":
            return float(self.value)
        return str(self.value)


@dataclass(slots=True)
class RuleModel:
    name: str
    expression: str
    source: str = "Manual"
    description: str = ""
    enabled: bool = True
    itl_template: str = ""
    itl_rule_name: str = ""
    controlled_components: list[str] = field(default_factory=list)
    original: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ScenarioModel:
    name: str
    values: dict[str, Any]


@dataclass(slots=True)
class ProjectModel:
    format_version: int = 1
    name: str = "Untitled"
    itl_source_path: str = ""
    selected_template: str = ""
    variables: list[VariableModel] = field(default_factory=list)
    rules: list[RuleModel] = field(default_factory=list)
    scenarios: list[ScenarioModel] = field(default_factory=list)
    ui_state: dict[str, Any] = field(default_factory=dict)
    project_path: str = ""
    dirty: bool = False

    def values(self) -> dict[str, Any]:
        return {variable.name: variable.typed_value() for variable in self.variables}

    def variable(self, name: str) -> VariableModel | None:
        folded = name.casefold()
        return next((variable for variable in self.variables if variable.name.casefold() == folded), None)

    def add_variable(self, variable: VariableModel) -> VariableModel:
        existing = self.variable(variable.name)
        if existing:
            return existing
        self.variables.append(variable)
        self.dirty = True
        return variable

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("project_path", None)
        data.pop("dirty", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectModel:
        return cls(
            format_version=int(data.get("format_version", 1)),
            name=str(data.get("name", "Untitled")),
            itl_source_path=str(data.get("itl_source_path", "")),
            selected_template=str(data.get("selected_template", "")),
            variables=[VariableModel(**item) for item in data.get("variables", [])],
            rules=[RuleModel(**item) for item in data.get("rules", [])],
            scenarios=[ScenarioModel(**item) for item in data.get("scenarios", [])],
            ui_state=dict(data.get("ui_state", {})),
        )
