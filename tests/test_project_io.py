from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.models.project import ProjectModel, RuleModel, ScenarioModel, VariableModel
from app.storage.project_io import load_project, save_project


class ProjectIOTests(unittest.TestCase):
    def test_round_trip_uses_separate_ordrule_file(self) -> None:
        project = ProjectModel(
            itl_source_path=r"C:\data\production.itl",
            selected_template="Folder/Template",
            variables=[VariableModel("GR_R", 0)],
            rules=[RuleModel("Guardrail", "GR_R < 1")],
            scenarios=[ScenarioModel("On", {"GR_R": 0})],
        )
        with TemporaryDirectory() as folder:
            target = save_project(project, Path(folder) / "test")
            self.assertEqual(target.suffix, ".ordrule")
            loaded = load_project(target)
            self.assertEqual(loaded.itl_source_path, project.itl_source_path)
            self.assertEqual(loaded.variables[0].name, "GR_R")
            self.assertEqual(loaded.rules[0].expression, "GR_R < 1")


if __name__ == "__main__":
    unittest.main()
