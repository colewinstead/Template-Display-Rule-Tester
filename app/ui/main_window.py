from __future__ import annotations

import csv
from difflib import get_close_matches
from pathlib import Path
import sys
from typing import Any

from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.engine.ast_nodes import format_ast
from app.engine.evaluator import EvaluationError, evaluate_ast
from app.engine.parser import ParseError, parse_expression
from app.itl.analyzer import point_usage
from app.itl.importer import import_rule
from app.itl.models import ITLComponent, ITLDisplayRule, ITLLibrary, ITLPoint, ITLTemplate
from app.itl.parser import ITLParseError, parse_itl
from app.models.project import ProjectModel, RuleModel, ScenarioModel, VariableModel
from app.storage.project_io import load_project, save_project

from .advanced import AdvancedPanel
from .panels import DebugPanel, ExplorerPanel, RulesPanel, VariablesPanel
from .styles import DARK_QSS, LIGHT_QSS


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Template Display Rule Tester")
        self.resize(1580, 960)
        self.setMinimumSize(1100, 700)
        self.settings = QSettings("VeriCivil", "TemplateDisplayRuleTester")
        self.project = ProjectModel()
        self.library: ITLLibrary | None = None
        self.current_template: ITLTemplate | None = None
        self.current_rule_index = -1
        # Engineering utilities are commonly used beside dark CAD viewports.
        # Launch dark by default while retaining the explicit View toggle.
        self.dark_mode = self.settings.value("darkMode", True, bool)
        self._build_ui()
        self._build_actions()
        self._connect_signals()
        self._apply_theme()
        self.set_project(self.project)
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        QTimer.singleShot(150, self._open_workspace_sample)

    def _build_ui(self) -> None:
        self.explorer = ExplorerPanel()
        self.variables = VariablesPanel()
        self.rules = RulesPanel()
        self.debug = DebugPanel()
        self.advanced = AdvancedPanel()
        center_tabs = QTabWidget()
        center_tabs.addTab(self.rules, "Display Rules")
        center_tabs.addTab(self.variables, "Variables / Points")
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(self.explorer)
        top_splitter.addWidget(center_tabs)
        top_splitter.addWidget(self.debug)
        top_splitter.setSizes([390, 670, 470])
        top_splitter.setStretchFactor(1, 2)
        vertical = QSplitter(Qt.Orientation.Vertical)
        vertical.addWidget(top_splitter)
        vertical.addWidget(self.advanced)
        vertical.setSizes([600, 320])
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(7, 7, 7, 7)
        layout.addWidget(vertical)
        self.setCentralWidget(container)
        self.statusBar().showMessage("Ready — production ITL files are always opened read-only")

    def _action(self, text: str, slot: Any, shortcut: str | None = None, checkable: bool = False) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        action.setCheckable(checkable)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        return action

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        new_action = self._action("&New Project", self.new_project, "Ctrl+N")
        open_itl_action = self._action("Open &ITL…", self.open_itl, "Ctrl+I")
        open_project_action = self._action("&Open Project…", self.open_project, "Ctrl+O")
        save_action = self._action("&Save Project", self.save, "Ctrl+S")
        save_as_action = self._action("Save Project &As…", self.save_as, "Ctrl+Shift+S")
        self.recent_menu = file_menu.addMenu("Recent Projects")
        for action in (new_action, open_itl_action, open_project_action, save_action, save_as_action): file_menu.addAction(action)
        file_menu.addSeparator()
        export_results = self._action("Export Rule Results CSV…", self.export_results)
        export_text = self._action("Export Rules as Text…", self.export_text)
        file_menu.addAction(export_results); file_menu.addAction(export_text)
        file_menu.addSeparator(); file_menu.addAction(self._action("E&xit", self.close, "Alt+F4"))
        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction(self._action("Add &Variable", self.variables.add_variable, "Ctrl+Shift+V"))
        edit_menu.addAction(self._action("Add &Rule", self.rules.add_rule, "Ctrl+Shift+R"))
        view_menu = self.menuBar().addMenu("&View")
        theme = self._action("Dark Mode", self.toggle_theme, "Ctrl+D", True)
        theme.setChecked(self.dark_mode)
        view_menu.addAction(theme)
        presets = self.menuBar().addMenu("&Presets")
        for name in ("Guardrail", "Cut / Fill", "Shoulder Width", "Point Control", "Null Point Trigger"):
            presets.addAction(self._action(name, lambda _checked=False, preset=name: self.load_preset(preset)))
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self._action("ITL Safety and Interpretation", self.show_safety))
        help_menu.addAction(self._action("About", self.show_about))
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        for action in (open_itl_action, open_project_action, save_action): toolbar.addAction(action)
        toolbar.addSeparator(); toolbar.addAction(self._action("Add Rule", self.rules.add_rule)); toolbar.addAction(self._action("Add Variable", self.variables.add_variable))
        self._refresh_recent()

    def _connect_signals(self) -> None:
        self.variables.variables_changed.connect(self.project_changed)
        self.rules.rules_changed.connect(self.project_changed)
        self.rules.rule_selected.connect(self.select_rule)
        self.explorer.object_selected.connect(self.explorer_selected)
        self.explorer.object_activated.connect(self.explorer_activated)
        self.advanced.project_changed.connect(self.project_changed)
        self.advanced.builder_generated.connect(self.add_built_rule)

    def _apply_theme(self) -> None:
        QApplication.instance().setStyleSheet(DARK_QSS if self.dark_mode else LIGHT_QSS)

    def toggle_theme(self, checked: bool) -> None:
        self.dark_mode = checked
        self.settings.setValue("darkMode", checked)
        self._apply_theme()

    def set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.variables.set_project(project)
        self.rules.set_project(project)
        self.advanced.set_project(project)
        self.current_rule_index = -1
        self.update_title()
        if project.itl_source_path and Path(project.itl_source_path).is_file():
            self.load_itl(project.itl_source_path, update_project=False)
        self.evaluate_all()

    def update_title(self) -> None:
        dirty = " *" if self.project.dirty else ""
        self.setWindowTitle(f"{self.project.name}{dirty} — Template Display Rule Tester")

    def project_changed(self) -> None:
        self.variables.refresh()
        self.evaluate_all()
        self.advanced.refresh()
        self.update_title()

    def new_project(self) -> None:
        if not self._confirm_discard(): return
        self.library = None; self.current_template = None; self.explorer.clear(); self.advanced.set_template(None)
        self.set_project(ProjectModel())
        self.statusBar().showMessage("New project created", 4000)

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Template Rule project", "", "Template Rule projects (*.ordrule);;JSON files (*.json)")
        if path: self.open_project_path(path)

    def open_project_path(self, path: str) -> None:
        if not self._confirm_discard(): return
        try:
            project = load_project(path)
        except ValueError as error:
            QMessageBox.warning(self, "Cannot open project", str(error)); return
        self.set_project(project); self._add_recent(path); self.statusBar().showMessage(f"Opened {path}", 5000)

    def save(self) -> bool:
        return self.save_to(self.project.project_path) if self.project.project_path else self.save_as()

    def save_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "Save Template Rule project", f"{self.project.name}.ordrule", "Template Rule projects (*.ordrule)")
        return self.save_to(path) if path else False

    def save_to(self, path: str) -> bool:
        try:
            target = save_project(self.project, path)
        except OSError as error:
            QMessageBox.warning(self, "Cannot save project", str(error)); return False
        self._add_recent(str(target)); self.update_title(); self.statusBar().showMessage(f"Saved {target}", 5000); return True

    def open_itl(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Bentley template library (read-only)", "", "Bentley template libraries (*.itl);;All files (*)")
        if path: self.load_itl(path)

    def load_itl(self, path: str, update_project: bool = True) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            library = parse_itl(path)
        except (ITLParseError, OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot read ITL", str(error)); return
        finally:
            QApplication.restoreOverrideCursor()
        self.library = library
        self.explorer.set_library(library)
        if update_project:
            self.project.itl_source_path = str(library.source_path)
            self.project.dirty = True
        selected = library.template(self.project.selected_template) if self.project.selected_template else None
        self.set_current_template(selected or (library.templates[0] if library.templates else None))
        counts = library.counts
        self.statusBar().showMessage(f"Read-only ITL loaded: {counts['templates']} templates, {counts['display_rules']} display rules — SHA-256 {library.sha256[:12]}…", 10000)
        self.update_title()

    def _open_workspace_sample(self) -> None:
        if self.library or self.project.itl_source_path: return
        sample = Path.cwd() / "rwd.itl"
        if sample.is_file(): self.load_itl(str(sample))

    def set_current_template(self, template: ITLTemplate | None) -> None:
        self.current_template = template
        self.advanced.set_template(template)
        if template:
            self.project.selected_template = template.path

    def explorer_selected(self, kind: str, payload: object) -> None:
        data = payload if isinstance(payload, tuple) else (payload,)
        if kind == "template":
            template = data[0]; self.set_current_template(template)
            details = f"Path: {template.path}\nOID: {template.oid or 'Not present'}\n\nPoints: {len(template.points)}\nComponents: {len(template.components)}\nDisplay rules: {len(template.display_rules)}\n\n{template.description or 'No description in ITL.'}"
            self.debug.show_object_details(template.name, details)
        elif kind == "point":
            point, template = data; self.set_current_template(template); usage = point_usage(template, point.name)
            lines = [f"Coordinates in ITL: X={point.x}, Y={point.y}", f"Feature: {point.feature_name or 'Not recorded'}", f"Style: {point.style or 'Not recorded'}", f"Null-point indicator: {'Yes' if point.is_null else 'No'}", "", "USED BY"]
            for group, names in usage.items(): lines.extend([f"{group}:"] + ([f"  • {name}" for name in names] or ["  None discovered"]))
            if point.constraints:
                lines.append("\nOWN CONSTRAINTS")
                lines.extend(f"  • {item.type}: value={item.value or '—'}, parent={item.parent or '—'}, parent2={item.parent2 or '—'}" for item in point.constraints)
            self.debug.show_object_details(point.name, "\n".join(lines))
        elif kind == "component":
            component, template = data; self.set_current_template(template)
            rules = component.rule_names or ["None resolved"]
            details = f"Type: {component.component_type or 'Not recorded'}\nMaterial: {component.material or 'Not recorded'}\nDisplay expression: {component.display_expression or 'Always / none recorded'}\n\nControlled by:\n" + "\n".join(f"  • {name}" for name in rules)
            if component.unresolved_expression: details += f"\n\nUnresolved source text: {component.unresolved_expression}"
            self.debug.show_object_details(component.name, details)
        elif kind == "rule":
            rule, template = data; self.set_current_template(template)
            details = f"Bentley type: {rule.rule_type}\nOriginal test: {rule.test or 'N/A'} {rule.value if rule.value is not None else ''}\nPoint/object 1: {rule.point1 or '—'}\nPoint/object 2: {rule.point2 or '—'}\n\nTester expression:\n{rule.tester_expression}\n\nUsed by:\n" + ("\n".join(f"  • {name}" for name in rule.used_by) or "  No component association found")
            self.debug.show_object_details(rule.name, details)
        elif kind == "library" and self.library:
            self.debug.show_object_details(self.library.source_path.name, f"Read-only source: {self.library.source_path}\nSHA-256: {self.library.sha256}\nFormat: InRoads XML, productVersion={self.library.product_version}\nUnits: {self.library.linear_units}, {self.library.angular_units}")

    def explorer_activated(self, kind: str, payload: object) -> None:
        data = payload if isinstance(payload, tuple) else (payload,)
        if kind == "rule": self.import_itl_rule(data[0], data[1])

    def import_itl_rule(self, itl_rule: ITLDisplayRule, template: ITLTemplate) -> None:
        existing = next((index for index, rule in enumerate(self.project.rules) if rule.itl_template == template.path and rule.itl_rule_name.casefold() == itl_rule.name.casefold()), None)
        if existing is not None:
            self.rules.table.selectRow(existing); self.statusBar().showMessage("That ITL rule is already loaded", 4000); return
        rule, variables = import_rule(template, itl_rule)
        for variable in variables: self.project.add_variable(variable)
        self.project.rules.append(rule); self.project.dirty = True
        self.variables.refresh(); self.rules.results.append((None, "")); self.evaluate_all(); self.advanced.refresh()
        self.rules.table.selectRow(len(self.project.rules) - 1)
        self.statusBar().showMessage(f"Imported {rule.name}; {len(variables)} referenced test coordinate(s) prepared", 6000)

    def evaluate_all(self) -> None:
        values = self.project.values()
        results: list[tuple[bool | None, str]] = []
        for rule in self.project.rules:
            if not rule.enabled:
                results.append((None, "Disabled")); continue
            try:
                result = evaluate_ast(parse_expression(rule.expression), values)
                results.append((result.value, ""))
            except (ParseError, EvaluationError) as error:
                results.append((None, str(error)))
        self.rules.set_results(results)
        if 0 <= self.current_rule_index < len(self.project.rules): self.select_rule(self.current_rule_index)

    def select_rule(self, index: int) -> None:
        self.current_rule_index = index
        if not (0 <= index < len(self.project.rules)): return
        rule = self.project.rules[index]
        relationship = self._rule_relationships(rule)
        try:
            ast = parse_expression(rule.expression)
            unknown = sorted(name for name in ast.variables() if self.project.variable(name) is None)
            if unknown:
                known = [variable.name for variable in self.project.variables]
                suggestions = []
                for name in unknown:
                    match = get_close_matches(name, known, n=1, cutoff=0.55)
                    suggestions.append(f"Unknown variable: {name}" + (f"\nDid you mean {match[0]}?" if match else ""))
                message = "\n\n".join(suggestions)
                self.rules.set_validation(message, False); self.debug.show_error(message, format_ast(ast), relationship); return
            result = evaluate_ast(ast, self.project.values())
            recognized = ", ".join(sorted(ast.variables())) or "No variables"
            self.rules.set_validation(f"Valid expression • Referenced: {recognized}", True)
            self.debug.show_result(result.value, result.explanation, result.ast_text, relationship)
        except ParseError as error:
            pointer = " " * error.position + "^"
            message = f"{error.message}\n{rule.expression}\n{pointer}"
            self.rules.set_validation(error.message, False); self.debug.show_error(message, "", relationship)
        except EvaluationError as error:
            self.rules.set_validation(str(error), False); self.debug.show_error(str(error), "", relationship)

    def _rule_relationships(self, rule: RuleModel) -> str:
        lines = [f"Source: {rule.source}"]
        if rule.itl_template: lines.append(f"ITL template: {rule.itl_template}")
        if rule.original:
            lines.append("\nOriginal Bentley attributes:")
            lines.extend(f"  {name}: {value}" for name, value in rule.original.items())
        lines.append("\nControlled components:")
        lines.extend([f"  • {name}" for name in rule.controlled_components] or ["  None supported by source associations"])
        return "\n".join(lines)

    def add_built_rule(self, expression: str) -> None:
        self.project.rules.append(RuleModel(f"Built Rule {len(self.project.rules) + 1}", expression))
        self.project.dirty = True; self.rules.results.append((None, "")); self.evaluate_all(); self.advanced.refresh(); self.rules.table.selectRow(len(self.project.rules) - 1)

    def load_preset(self, name: str) -> None:
        presets: dict[str, tuple[list[VariableModel], list[RuleModel], list[ScenarioModel]]] = {
            "Guardrail": ([VariableModel("GR_R"), VariableModel("FIND_GR_R") , VariableModel("SHOULDER_WIDTH", 8)], [RuleModel("Guardrail Required", "FIND_GR_R > 0 AND GR_R < 1", "Preset")], [ScenarioModel("Guardrail Required", {"GR_R": 0, "FIND_GR_R": 12, "SHOULDER_WIDTH": 8})]),
            "Cut / Fill": ([VariableModel("CUT_DEPTH"), VariableModel("FILL_DEPTH")], [RuleModel("Cut", "CUT_DEPTH > 0", "Preset"), RuleModel("Fill", "FILL_DEPTH > 0", "Preset")], []),
            "Shoulder Width": ([VariableModel("SHOULDER_WIDTH", 8)], [RuleModel("Full Shoulder", "SHOULDER_WIDTH >= 8", "Preset")], []),
            "Point Control": ([VariableModel("CONTROL_OFFSET"), VariableModel("CONTROL_ACTIVE", False, "Boolean")], [RuleModel("Point Controlled", "CONTROL_ACTIVE = TRUE AND CONTROL_OFFSET != 0", "Preset")], []),
            "Null Point Trigger": ([VariableModel("NULL_POINT_OFFSET")], [RuleModel("Null Point Trigger", "NOT (NULL_POINT_OFFSET = 0)", "Preset")], []),
        }
        variables, rules, scenarios = presets[name]
        for variable in variables: self.project.add_variable(variable)
        self.project.rules.extend(rules); self.project.scenarios.extend(scenarios); self.project.dirty = True
        self.variables.refresh(); self.rules.set_project(self.project); self.advanced.set_project(self.project); self.evaluate_all(); self.update_title()

    def export_results(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export current rule results", "rule-results.csv", "CSV files (*.csv)")
        if not path: return
        values = self.project.values()
        with Path(path).open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream); writer.writerow(["Rule", "Expression", "Result", "Source", "Description"])
            for rule in self.project.rules:
                try: result = str(evaluate_ast(parse_expression(rule.expression), values).value).upper() if rule.enabled else "DISABLED"
                except (ParseError, EvaluationError) as error: result = f"ERROR: {error}"
                writer.writerow([rule.name, rule.expression, result, rule.source, rule.description])
        self.statusBar().showMessage(f"Exported {path}", 5000)

    def export_text(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export rules", "display-rules.txt", "Text files (*.txt)")
        if not path: return
        blocks = [f"RULE: {rule.name}\nSOURCE: {rule.source}\n\n{rule.expression}" for rule in self.project.rules]
        Path(path).write_text("\n\n" + ("\n\n" + "-" * 72 + "\n\n").join(blocks), encoding="utf-8")

    def _confirm_discard(self) -> bool:
        if not self.project.dirty: return True
        choice = QMessageBox.question(self, "Unsaved changes", "Save changes to the current tester project?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if choice == QMessageBox.StandardButton.Save: return self.save()
        return choice == QMessageBox.StandardButton.Discard

    def _recent_paths(self) -> list[str]:
        value = self.settings.value("recentProjects", [])
        return [str(item) for item in (value if isinstance(value, list) else [value]) if item]

    def _add_recent(self, path: str) -> None:
        paths = [path] + [item for item in self._recent_paths() if item.casefold() != path.casefold()]
        self.settings.setValue("recentProjects", paths[:10]); self._refresh_recent()

    def _refresh_recent(self) -> None:
        self.recent_menu.clear()
        paths = [path for path in self._recent_paths() if Path(path).is_file()]
        if not paths:
            empty = QAction("No recent projects", self); empty.setEnabled(False); self.recent_menu.addAction(empty)
        for path in paths: self.recent_menu.addAction(self._action(path, lambda _checked=False, item=path: self.open_project_path(item)))

    def show_safety(self) -> None:
        QMessageBox.information(self, "ITL Safety and Interpretation", "ITL libraries are opened read-only. Tester projects are saved separately as .ordrule JSON files.\n\nThe sample encodes atomic rules as Bentley XML attributes. HDIFF/VDIFF/absolute difference and SLOPE make the tester calculation visible. The exact Bentley runtime, point-control resolution, and degenerate-slope behavior are not guaranteed by the XML alone; validate critical production decisions in OpenRoads Designer.")

    def show_about(self) -> None:
        QMessageBox.about(self, "About Template Display Rule Tester", "Template Display Rule Tester 1.0\n\nA read-only OpenRoads template inspector and safe display-rule debugger.")

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._confirm_discard(): event.ignore(); return
        self.settings.setValue("geometry", self.saveGeometry()); event.accept()


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Template Display Rule Tester")
    app.setOrganizationName("VeriCivil")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()
