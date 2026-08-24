from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.engine.evaluator import EvaluationError
from app.engine.rule_analyzer import compare_rules, conflict_scan, matrix, numeric_values, sweep, transitions, truth_table
from app.itl.analyzer import template_diagnostics
from app.itl.models import ITLTemplate
from app.models.project import ProjectModel, ScenarioModel


def _spin(value: float, minimum: float = -1_000_000, maximum: float = 1_000_000) -> QDoubleSpinBox:
    widget = QDoubleSpinBox()
    widget.setDecimals(6)
    widget.setRange(minimum, maximum)
    widget.setValue(value)
    return widget


def _fill_table(table: QTableWidget, headers: list[str], rows: list[list[Any]]) -> None:
    table.clear()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column, value in enumerate(row):
            table.setItem(row_index, column, QTableWidgetItem(str(value)))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


class AdvancedPanel(QWidget):
    project_changed = Signal()
    builder_generated = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.project: ProjectModel | None = None
        self.template: ITLTemplate | None = None
        self._range_rows: list[list[Any]] = []
        layout = QVBoxLayout(self)
        heading = QLabel("ADVANCED TESTING TOOLS")
        heading.setStyleSheet("font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(heading)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._build_range()
        self._build_matrix()
        self._build_compare()
        self._build_conflicts()
        self._build_scenarios()
        self._build_truth()
        self._build_builder()
        self._build_diagnostics()

    def _rule_combo(self) -> QComboBox:
        return QComboBox()

    def _variable_combo(self) -> QComboBox:
        return QComboBox()

    def _build_range(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        self.range_rule = self._rule_combo()
        self.range_variable = self._variable_combo()
        self.range_start, self.range_end, self.range_step = _spin(-10), _spin(10), _spin(1, -1e6, 1e6)
        for label, widget in (("Rule", self.range_rule), ("Variable", self.range_variable), ("Start", self.range_start), ("End", self.range_end), ("Step", self.range_step)):
            controls.addWidget(QLabel(label))
            controls.addWidget(widget)
        run = QPushButton("Run sweep")
        run.setObjectName("accent")
        export = QPushButton("Export CSV")
        controls.addWidget(run)
        controls.addWidget(export)
        layout.addLayout(controls)
        self.range_summary = QLabel("Sweep one numeric variable to find state transitions.")
        layout.addWidget(self.range_summary)
        self.range_table = QTableWidget()
        layout.addWidget(self.range_table)
        run.clicked.connect(self.run_range)
        export.clicked.connect(self.export_range)
        self.tabs.addTab(page, "Range Test")

    def _build_matrix(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        grid = QGridLayout()
        self.matrix_rule = self._rule_combo()
        self.matrix_a, self.matrix_b = self._variable_combo(), self._variable_combo()
        self.matrix_a_start, self.matrix_a_end, self.matrix_a_step = _spin(-2), _spin(2), _spin(1)
        self.matrix_b_start, self.matrix_b_end, self.matrix_b_step = _spin(0), _spin(15), _spin(5)
        grid.addWidget(QLabel("Rule"), 0, 0)
        grid.addWidget(self.matrix_rule, 0, 1, 1, 5)
        for row, label, combo, start, end, step in ((1, "Rows", self.matrix_a, self.matrix_a_start, self.matrix_a_end, self.matrix_a_step), (2, "Columns", self.matrix_b, self.matrix_b_start, self.matrix_b_end, self.matrix_b_step)):
            grid.addWidget(QLabel(label), row, 0); grid.addWidget(combo, row, 1)
            grid.addWidget(QLabel("Start"), row, 2); grid.addWidget(start, row, 3)
            grid.addWidget(QLabel("End / Step"), row, 4)
            box = QWidget(); box_layout = QHBoxLayout(box); box_layout.setContentsMargins(0, 0, 0, 0); box_layout.addWidget(end); box_layout.addWidget(step)
            grid.addWidget(box, row, 5)
        run = QPushButton("Build matrix")
        run.setObjectName("accent")
        grid.addWidget(run, 0, 6, 3, 1)
        layout.addLayout(grid)
        self.matrix_table = QTableWidget()
        layout.addWidget(self.matrix_table)
        run.clicked.connect(self.run_matrix)
        self.tabs.addTab(page, "Logic Matrix")

    def _build_compare(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.compare_a, self.compare_b = self._rule_combo(), self._rule_combo()
        self.compare_variable = self._variable_combo()
        self.compare_start, self.compare_end, self.compare_step = _spin(-100), _spin(100), _spin(1)
        form.addRow("Expression A", self.compare_a); form.addRow("Expression B", self.compare_b); form.addRow("Sweep variable", self.compare_variable)
        row = QWidget(); row_layout = QHBoxLayout(row); row_layout.setContentsMargins(0, 0, 0, 0)
        for label, widget in (("Start", self.compare_start), ("End", self.compare_end), ("Step", self.compare_step)):
            row_layout.addWidget(QLabel(label)); row_layout.addWidget(widget)
        form.addRow("Range", row)
        layout.addLayout(form)
        run = QPushButton("Compare rules")
        run.setObjectName("accent")
        layout.addWidget(run)
        self.compare_result = QLabel("Choose two rules and a numeric variable.")
        self.compare_result.setWordWrap(True)
        layout.addWidget(self.compare_result)
        self.compare_table = QTableWidget()
        layout.addWidget(self.compare_table)
        run.clicked.connect(self.run_compare)
        self.tabs.addTab(page, "Compare")

    def _build_conflicts(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        self.conflict_variable = self._variable_combo()
        self.conflict_start, self.conflict_end, self.conflict_step = _spin(-10), _spin(10), _spin(1)
        for label, widget in (("Variable", self.conflict_variable), ("Start", self.conflict_start), ("End", self.conflict_end), ("Step", self.conflict_step)):
            controls.addWidget(QLabel(label)); controls.addWidget(widget)
        run = QPushButton("Check enabled rules")
        run.setObjectName("accent")
        controls.addWidget(run)
        layout.addLayout(controls)
        self.conflict_summary = QLabel("A gap has no active rule; an overlap has more than one active rule.")
        layout.addWidget(self.conflict_summary)
        self.conflict_table = QTableWidget()
        layout.addWidget(self.conflict_table)
        run.clicked.connect(self.run_conflicts)
        self.tabs.addTab(page, "Conflict / Gap")

    def _build_scenarios(self) -> None:
        page = QWidget()
        layout = QHBoxLayout(page)
        left = QVBoxLayout()
        self.scenario_list = QListWidget()
        left.addWidget(self.scenario_list)
        self.scenario_name = QLineEdit()
        self.scenario_name.setPlaceholderText("Scenario name")
        left.addWidget(self.scenario_name)
        buttons = QHBoxLayout()
        save, load, delete = QPushButton("Save current"), QPushButton("Load"), QPushButton("Delete")
        buttons.addWidget(save); buttons.addWidget(load); buttons.addWidget(delete)
        left.addLayout(buttons)
        layout.addLayout(left, 1)
        self.scenario_values = QTableWidget()
        layout.addWidget(self.scenario_values, 2)
        self.scenario_list.currentRowChanged.connect(self._show_scenario)
        save.clicked.connect(self.save_scenario); load.clicked.connect(self.load_scenario); delete.clicked.connect(self.delete_scenario)
        self.tabs.addTab(page, "Scenarios")

    def _build_truth(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        self.truth_rule = self._rule_combo()
        controls.addWidget(QLabel("Boolean rule")); controls.addWidget(self.truth_rule, 1)
        run = QPushButton("Generate truth table")
        run.setObjectName("accent")
        controls.addWidget(run)
        layout.addLayout(controls)
        self.truth_table_widget = QTableWidget()
        layout.addWidget(self.truth_table_widget)
        run.clicked.connect(self.run_truth)
        self.tabs.addTab(page, "Truth Table")

    def _build_builder(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Build a two-condition rule. The generated expression remains fully editable."))
        grid = QGridLayout()
        self.builder_not_a, self.builder_not_b = QCheckBox("NOT"), QCheckBox("NOT")
        self.builder_var_a, self.builder_var_b = self._variable_combo(), self._variable_combo()
        self.builder_op_a, self.builder_op_b = QComboBox(), QComboBox()
        self.builder_op_a.addItems(["<", ">", "<=", ">=", "=", "!="]); self.builder_op_b.addItems(["<", ">", "<=", ">=", "=", "!="])
        self.builder_value_a, self.builder_value_b = QLineEdit("0"), QLineEdit("0")
        self.builder_join = QComboBox(); self.builder_join.addItems(["AND", "OR"])
        for row, widgets in enumerate(((self.builder_not_a, self.builder_var_a, self.builder_op_a, self.builder_value_a), (self.builder_not_b, self.builder_var_b, self.builder_op_b, self.builder_value_b))):
            for column, widget in enumerate(widgets): grid.addWidget(widget, row * 2, column)
            if row == 0: grid.addWidget(self.builder_join, 1, 1)
        layout.addLayout(grid)
        generate = QPushButton("Generate and add rule")
        generate.setObjectName("accent")
        layout.addWidget(generate)
        self.builder_preview = QLineEdit()
        self.builder_preview.setReadOnly(True)
        layout.addWidget(self.builder_preview)
        layout.addStretch()
        generate.clicked.connect(self.generate_builder)
        for widget in (self.builder_not_a, self.builder_not_b, self.builder_var_a, self.builder_var_b, self.builder_op_a, self.builder_op_b, self.builder_value_a, self.builder_value_b, self.builder_join):
            if isinstance(widget, QLineEdit): widget.textChanged.connect(self.update_builder_preview)
            elif isinstance(widget, QCheckBox): widget.toggled.connect(self.update_builder_preview)
            else: widget.currentTextChanged.connect(self.update_builder_preview)
        self.tabs.addTab(page, "Rule Builder")

    def _build_diagnostics(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.diagnostic_summary = QLabel("Select an ITL template to inspect justified source-data issues.")
        layout.addWidget(self.diagnostic_summary)
        self.diagnostic_table = QTableWidget()
        layout.addWidget(self.diagnostic_table)
        self.tabs.addTab(page, "ITL Diagnostics")

    def set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.refresh()

    def set_template(self, template: ITLTemplate | None) -> None:
        self.template = template
        self.refresh_diagnostics()

    def refresh(self) -> None:
        rule_combos = [self.range_rule, self.matrix_rule, self.compare_a, self.compare_b, self.truth_rule]
        variable_combos = [self.range_variable, self.matrix_a, self.matrix_b, self.compare_variable, self.conflict_variable, self.builder_var_a, self.builder_var_b]
        old_rules = [combo.currentText() for combo in rule_combos]
        old_variables = [combo.currentText() for combo in variable_combos]
        for combo, old in zip(rule_combos, old_rules, strict=True):
            combo.clear()
            if self.project:
                combo.addItems([rule.name for rule in self.project.rules if rule.enabled])
            combo.setCurrentText(old)
        for combo, old in zip(variable_combos, old_variables, strict=True):
            combo.clear()
            if self.project:
                combo.addItems([variable.name for variable in self.project.variables])
            combo.setCurrentText(old)
        self.scenario_list.clear()
        if self.project:
            self.scenario_list.addItems([scenario.name for scenario in self.project.scenarios])
        self.update_builder_preview()

    def _rule(self, combo: QComboBox):
        if not self.project:
            return None
        return next((rule for rule in self.project.rules if rule.name == combo.currentText()), None)

    def _error(self, error: Exception) -> None:
        QMessageBox.warning(self, "Test could not run", str(error))

    def run_range(self) -> None:
        rule = self._rule(self.range_rule)
        if not self.project or not rule or not self.range_variable.currentText(): return
        try:
            rows = sweep(rule.expression, self.range_variable.currentText(), self.range_start.value(), self.range_end.value(), self.range_step.value(), self.project.values())
            self._range_rows = [[f"{row.value:g}", "ERROR" if row.result is None else str(row.result).upper(), row.error] for row in rows]
            _fill_table(self.range_table, [self.range_variable.currentText(), "Result", "Details"], self._range_rows)
            changes = transitions(rows)
            self.range_summary.setText("Transitions: " + ("; ".join(changes) if changes else "none in this sampled range"))
        except (ValueError, EvaluationError) as error: self._error(error)

    def export_range(self) -> None:
        if not self._range_rows: return
        path, _ = QFileDialog.getSaveFileName(self, "Export range test", "range-test.csv", "CSV files (*.csv)")
        if not path: return
        with Path(path).open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream); writer.writerow([self.range_variable.currentText(), "Result", "Details"]); writer.writerows(self._range_rows)

    def run_matrix(self) -> None:
        rule = self._rule(self.matrix_rule)
        if not self.project or not rule: return
        try:
            a_values = numeric_values(self.matrix_a_start.value(), self.matrix_a_end.value(), self.matrix_a_step.value(), 100)
            b_values = numeric_values(self.matrix_b_start.value(), self.matrix_b_end.value(), self.matrix_b_step.value(), 100)
            if len(a_values) * len(b_values) > 2500: raise ValueError("Matrix is limited to 2,500 cells")
            values = matrix(rule.expression, self.matrix_a.currentText(), a_values, self.matrix_b.currentText(), b_values, self.project.values())
            rows = [[f"{a:g}"] + [("T" if result else "F") for result in row] for a, row in zip(a_values, values, strict=True)]
            _fill_table(self.matrix_table, [f"{self.matrix_a.currentText()} \\ {self.matrix_b.currentText()}"] + [f"{b:g}" for b in b_values], rows)
        except (ValueError, EvaluationError) as error: self._error(error)

    def run_compare(self) -> None:
        first, second = self._rule(self.compare_a), self._rule(self.compare_b)
        if not self.project or not first or not second: return
        try:
            differences = compare_rules(first.expression, second.expression, self.compare_variable.currentText(), self.compare_start.value(), self.compare_end.value(), self.compare_step.value(), self.project.values())
            if differences:
                self.compare_result.setText(f"The rules differ at {len(differences)} sampled value(s).")
                _fill_table(self.compare_table, [self.compare_variable.currentText(), first.name, second.name], [[f"{v:g}", str(a).upper(), str(b).upper()] for v, a, b in differences])
            else:
                self.compare_result.setText(f"Equivalent across sampled values {self.compare_start.value():g} through {self.compare_end.value():g}. This is a sampled-range result, not a formal proof.")
                _fill_table(self.compare_table, ["Result"], [["No differences found"]])
        except (ValueError, EvaluationError) as error: self._error(error)

    def run_conflicts(self) -> None:
        if not self.project: return
        rules = [(rule.name, rule.expression) for rule in self.project.rules if rule.enabled]
        try:
            findings = conflict_scan(rules, self.conflict_variable.currentText(), self.conflict_start.value(), self.conflict_end.value(), self.conflict_step.value(), self.project.values())
            _fill_table(self.conflict_table, [self.conflict_variable.currentText(), "Finding", "Active rules"], [[f"{value:g}", kind, ", ".join(names) or "None"] for value, kind, names in findings])
            self.conflict_summary.setText(f"{len(findings)} possible gap/overlap sample(s) found." if findings else "Exactly one enabled rule was TRUE at every sampled value.")
        except (ValueError, EvaluationError) as error: self._error(error)

    def save_scenario(self) -> None:
        if not self.project: return
        name = self.scenario_name.text().strip() or f"Scenario {len(self.project.scenarios) + 1}"
        existing = next((item for item in self.project.scenarios if item.name.casefold() == name.casefold()), None)
        if existing: existing.values = self.project.values()
        else: self.project.scenarios.append(ScenarioModel(name, self.project.values()))
        self.project.dirty = True; self.refresh(); self.project_changed.emit()

    def _show_scenario(self, row: int) -> None:
        if not self.project or not (0 <= row < len(self.project.scenarios)):
            _fill_table(self.scenario_values, ["Variable", "Value"], []); return
        scenario = self.project.scenarios[row]
        self.scenario_name.setText(scenario.name)
        _fill_table(self.scenario_values, ["Variable", "Value"], [[name, value] for name, value in scenario.values.items()])

    def load_scenario(self) -> None:
        if not self.project or self.scenario_list.currentRow() < 0: return
        scenario = self.project.scenarios[self.scenario_list.currentRow()]
        for name, value in scenario.values.items():
            variable = self.project.variable(name)
            if variable: variable.value = value
        self.project.dirty = True; self.project_changed.emit()

    def delete_scenario(self) -> None:
        if not self.project or self.scenario_list.currentRow() < 0: return
        del self.project.scenarios[self.scenario_list.currentRow()]
        self.project.dirty = True; self.refresh(); self.project_changed.emit()

    def run_truth(self) -> None:
        rule = self._rule(self.truth_rule)
        if not rule: return
        try:
            rows = truth_table(rule.expression)
            names = sorted(rows[0][0]) if rows else []
            _fill_table(self.truth_table_widget, names + ["Result"], [[str(values[name]).upper() for name in names] + [str(result).upper()] for values, result in rows])
        except (ValueError, EvaluationError) as error: self._error(error)

    def update_builder_preview(self, *_args: Any) -> None:
        first = f"{'NOT ' if self.builder_not_a.isChecked() else ''}({self.builder_var_a.currentText()} {self.builder_op_a.currentText()} {self.builder_value_a.text() or '0'})"
        second = f"{'NOT ' if self.builder_not_b.isChecked() else ''}({self.builder_var_b.currentText()} {self.builder_op_b.currentText()} {self.builder_value_b.text() or '0'})"
        self.builder_preview.setText(f"{first} {self.builder_join.currentText()} {second}")

    def generate_builder(self) -> None:
        self.update_builder_preview()
        self.builder_generated.emit(self.builder_preview.text())

    def refresh_diagnostics(self) -> None:
        if not self.template:
            self.diagnostic_summary.setText("Select an ITL template to inspect justified source-data issues.")
            _fill_table(self.diagnostic_table, ["Severity", "Object", "Finding"], [])
            return
        findings = template_diagnostics(self.template)
        self.diagnostic_summary.setText(f"{self.template.name}: {len(self.template.points)} points, {len(self.template.components)} components, {len(self.template.display_rules)} display rules; {len(findings)} justified finding(s).")
        _fill_table(self.diagnostic_table, ["Severity", "Object", "Finding"], [[item.severity, item.object_name, item.message] for item in findings])
