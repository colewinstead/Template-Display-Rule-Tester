from __future__ import annotations

import json
from pathlib import Path

from app.models.project import ProjectModel


def save_project(project: ProjectModel, path: str | Path) -> Path:
    target = Path(path).expanduser().resolve()
    if target.suffix.casefold() != ".ordrule":
        target = target.with_suffix(".ordrule")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(project.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)
    project.project_path = str(target)
    project.name = target.stem
    project.dirty = False
    return target


def load_project(path: str | Path) -> ProjectModel:
    source = Path(path).expanduser().resolve()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot open project: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("Project root must be a JSON object")
    project = ProjectModel.from_dict(data)
    project.project_path = str(source)
    project.name = source.stem
    project.dirty = False
    return project
