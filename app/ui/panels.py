from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.itl.models import ITLComponent, ITLDisplayRule, ITLLibrary, ITLPoint, ITLTemplate
from app.models.project import ProjectModel, RuleModel, VariableModel


DATA_ROLE = Qt.ItemDataRole.UserRole


class ExplorerPanel(QWidget):
    object_selected = Signal(str, object)
    object_activated = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("ITL EXPLORER")
        title.setStyleSheet("font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(title)
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search templates, points, components, rules…")
        self.search.setClearButtonEnabled(True)
        self.filter = QComboBox()
        self.filter.addItems(["All objects", "Templates", "Points", "Components", "Display rules"])
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.filter)
        layout.addLayout(search_row)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Library object", "Type"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree, 1)
        self.summary = QLabel("Open an ITL template library to begin.")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.search.textChanged.connect(self._apply_filter)
        self.filter.currentTextChanged.connect(self._apply_filter)
        self.tree.currentItemChanged.connect(self._selected)
        self.tree.itemDoubleClicked.connect(self._activated)

    def clear(self) -> None:
        self.tree.clear()
        self.summary.setText("Open an ITL template library to begin.")

    def set_library(self, library: ITLLibrary) -> None:
        self.tree.clear()
        root = QTreeWidgetItem([library.source_path.name, "Library"])
        root.setData(0, DATA_ROLE, ("library", library))
        self.tree.addTopLevelItem(root)
        category_items: dict[tuple[str, ...], QTreeWidgetItem] = {(): root}
        for template in library.templates:
            current_path: tuple[str, ...] = ()
            parent = root
            for part in template.category_path:
                current_path += (part,)
                if current_path not in category_items:
                    category_items[current_path] = QTreeWidgetItem(parent, [part, "Folder"])
                parent = category_items[current_path]
            template_item = QTreeWidgetItem(parent, [template.name, "Template"])
            template_item.setData(0, DATA_ROLE, ("template", template))
            points_item = QTreeWidgetItem(template_item, [f"Points ({len(template.points)})", "Group"])
            for point in template.points:
                item = QTreeWidgetItem(points_item, [point.name, "Null point" if point.is_null else "Point"])
                item.setData(0, DATA_ROLE, ("point", point, template))
            components_item = QTreeWidgetItem(template_item, [f"Components ({len(template.components)})", "Group"])
            for component in template.components:
                item = QTreeWidgetItem(components_item, [component.name, "Component"])
                item.setData(0, DATA_ROLE, ("component", component, template))
            rules_item = QTreeWidgetItem(template_item, [f"Display Rules ({len(template.display_rules)})", "Group"])
            for rule in template.display_rules:
                item = QTreeWidgetItem(rules_item, [rule.name, "Display rule"])
                item.setData(0, DATA_ROLE, ("rule", rule, template))
        root.setExpanded(True)
        self.summary.setText(
            f"{len(library.templates):,} templates  •  {library.counts['points']:,} points  •  "
            f"{library.counts['components']:,} components  •  {library.counts['display_rules']:,} rules"
        )
        self._apply_filter()

    def _selected(self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None) -> None:
        if not current:
            return
        data = current.data(0, DATA_ROLE)
        if data:
            self.object_selected.emit(data[0], data[1:])

    def _activated(self, item: QTreeWidgetItem, _column: int) -> None:
        data = item.data(0, DATA_ROLE)
        if data:
            self.object_activated.emit(data[0], data[1:])

    def _apply_filter(self, *_args: Any) -> None:
        query = self.search.text().strip().casefold()
        selected_type = self.filter.currentText()
        allowed = {
            "All objects": None,
            "Templates": {"Template"},
            "Points": {"Point", "Null point"},
            "Components": {"Component"},
            "Display rules": {"Display rule"},
        }[selected_type]

        def visit(item: QTreeWidgetItem) -> bool:
            child_visible = any(visit(item.child(i)) for i in range(item.childCount()))
            own_type = item.text(1)
            own_match = (not query or query in item.text(0).casefold()) and (allowed is None or own_type in allowed)
            visible = own_match or child_visible
            item.setHidden(not visible)
            if query and child_visible:
                item.setExpanded(True)
            return visible

        for index in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(index))


class VariablesPanel(QWidget):
    variables_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.project: ProjectModel | None = None
        self._updating = False
        layout = QVBoxLayout(self)
        heading = QHBoxLayout()
        title = QLabel("TEST VARIABLES / TEMPLATE POINTS")
        title.setStyleSheet("font-weight: 700; letter-spacing: 1px;")
        heading.addWidget(title)
        heading.addStretch()
        self.add_button = QPushButton("Add")
        self.duplicate_button = QPushButton("Duplicate")
        self.delete_button = QPushButton("Delete")
        heading.addWidget(self.add_button)
        heading.addWidget(self.duplicate_button)
        heading.addWidget(self.delete_button)
        layout.addLayout(heading)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Name", "Value", "Type", "Source", "Description", "Min", "Max", "Step"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)
        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Selected value"))
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setDecimals(6)
        self.value_spin.setRange(-1e9, 1e9)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        slider_row.addWidget(self.value_spin)
        slider_row.addWidget(self.slider, 1)
        layout.addLayout(slider_row)
        note = QLabel("ITL values are editable test coordinates only; the source .itl is never changed.")
        note.setStyleSheet("color: #64727e; font-style: italic;")
        layout.addWidget(note)
        self.add_button.clicked.connect(self.add_variable)
        self.duplicate_button.clicked.connect(self.duplicate_variable)
        self.delete_button.clicked.connect(self.delete_variable)
        self.table.itemChanged.connect(self._item_changed)
        self.table.currentCellChanged.connect(self._selection_changed)
        self.value_spin.valueChanged.connect(self._spin_changed)
        self.slider.valueChanged.connect(self._slider_changed)

    def set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.refresh()

    def refresh(self) -> None:
        self._updating = True
        self.table.setRowCount(0)
        if self.project:
            for variable in self.project.variables:
                row = self.table.rowCount()
                self.table.insertRow(row)
                values = [variable.name, str(variable.value), variable.value_type, variable.source, variable.description, str(variable.minimum), str(variable.maximum), str(variable.step)]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if variable.source.startswith("ITL") and column in {0, 2, 3}:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, column, item)
        self._updating = False
        self._selection_changed(self.table.currentRow(), 0, -1, -1)

    def add_variable(self) -> None:
        if not self.project:
            return
        base = "VARIABLE"
        index = 1
        while self.project.variable(f"{base}_{index}"):
            index += 1
        self.project.variables.append(VariableModel(f"{base}_{index}"))
        self.project.dirty = True
        self.refresh()
        self.table.selectRow(len(self.project.variables) - 1)
        self.variables_changed.emit()

    def duplicate_variable(self) -> None:
        if not self.project or self.table.currentRow() < 0:
            return
        source = self.project.variables[self.table.currentRow()]
        index = 2
        name = f"{source.name}_COPY"
        while self.project.variable(name):
            name = f"{source.name}_COPY{index}"
            index += 1
        self.project.variables.append(VariableModel(name, source.value, source.value_type, "Manual", source.description, source.minimum, source.maximum, source.step))
        self.project.dirty = True
        self.refresh()
        self.variables_changed.emit()

    def delete_variable(self) -> None:
        if not self.project or self.table.currentRow() < 0:
            return
        variable = self.project.variables[self.table.currentRow()]
        if variable.source.startswith("ITL"):
            return
        del self.project.variables[self.table.currentRow()]
        self.project.dirty = True
        self.refresh()
        self.variables_changed.emit()

    def _item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating or not self.project or item.row() >= len(self.project.variables):
            return
        variable = self.project.variables[item.row()]
        try:
            if item.column() == 0:
                new_name = item.text().strip()
                if not new_name or (self.project.variable(new_name) and new_name.casefold() != variable.name.casefold()):
                    raise ValueError("Variable names must be unique and non-empty")
                variable.name = new_name
            elif item.column() == 1:
                if variable.value_type == "Boolean":
                    variable.value = item.text().strip().casefold() in {"true", "1", "yes", "on"}
                elif variable.value_type == "Number":
                    variable.value = float(item.text())
                else:
                    variable.value = item.text()
            elif item.column() == 2:
                value_type = item.text().title()
                if value_type not in {"Number", "Boolean", "Text"}:
                    raise ValueError("Type must be Number, Boolean, or Text")
                variable.value_type = value_type
            elif item.column() == 4:
                variable.description = item.text()
            elif item.column() == 5:
                variable.minimum = float(item.text())
            elif item.column() == 6:
                variable.maximum = float(item.text())
            elif item.column() == 7:
                variable.step = float(item.text())
            self.project.dirty = True
            self.variables_changed.emit()
            self._selection_changed(item.row(), item.column(), -1, -1)
        except ValueError:
            self.refresh()

    def _selection_changed(self, row: int, _column: int, _previous_row: int, _previous_column: int) -> None:
        if not self.project or not (0 <= row < len(self.project.variables)):
            self.slider.setEnabled(False)
            self.value_spin.setEnabled(False)
            return
        variable = self.project.variables[row]
        numeric = variable.value_type == "Number" and variable.maximum > variable.minimum
        self.slider.setEnabled(numeric)
        self.value_spin.setEnabled(numeric)
        if numeric:
            self._updating = True
            self.value_spin.setRange(variable.minimum, variable.maximum)
            self.value_spin.setSingleStep(variable.step if variable.step > 0 else 0.1)
            self.value_spin.setValue(float(variable.value))
            position = round((float(variable.value) - variable.minimum) / (variable.maximum - variable.minimum) * 1000)
            self.slider.setValue(max(0, min(1000, position)))
            self._updating = False

    def _spin_changed(self, value: float) -> None:
        if self._updating or not self.project or self.table.currentRow() < 0:
            return
        variable = self.project.variables[self.table.currentRow()]
        variable.value = value
        self.project.dirty = True
        self.refresh()
        self.table.selectRow(self.project.variables.index(variable))
        self.variables_changed.emit()

    def _slider_changed(self, position: int) -> None:
        if self._updating or not self.project or self.table.currentRow() < 0:
            return
        variable = self.project.variables[self.table.currentRow()]
        value = variable.minimum + (variable.maximum - variable.minimum) * position / 1000
        if variable.step > 0:
            value = round(value / variable.step) * variable.step
        self._spin_changed(value)


class RulesPanel(QWidget):
    rule_selected = Signal(int)
    rules_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.project: ProjectModel | None = None
        self.results: list[tuple[bool | None, str]] = []
        self._updating = False
        layout = QVBoxLayout(self)
        heading = QHBoxLayout()
        title = QLabel("DISPLAY RULES")
        title.setStyleSheet("font-weight: 700; letter-spacing: 1px;")
        heading.addWidget(title)
        heading.addStretch()
        self.add_button = QPushButton("Add rule")
        self.duplicate_button = QPushButton("Duplicate")
        self.delete_button = QPushButton("Delete")
        heading.addWidget(self.add_button)
        heading.addWidget(self.duplicate_button)
        heading.addWidget(self.delete_button)
        layout.addLayout(heading)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["On", "Rule", "Expression", "Status", "Source"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)
        metadata = QHBoxLayout()
        metadata.addWidget(QLabel("Rule name"))
        self.name_editor = QLineEdit()
        metadata.addWidget(self.name_editor, 1)
        metadata.addWidget(QLabel("Description"))
        self.description_editor = QLineEdit()
        self.description_editor.setPlaceholderText("Optional engineering note")
        metadata.addWidget(self.description_editor, 2)
        layout.addLayout(metadata)
        layout.addWidget(QLabel("Expression (live validation)"))
        self.editor = QPlainTextEdit()
        self.editor.setMaximumHeight(92)
        self.editor.setPlaceholderText("Example: FIND_GR_R > 0 AND GR_R < 1")
        layout.addWidget(self.editor)
        self.validation = QLabel("Select a rule to inspect it.")
        self.validation.setWordWrap(True)
        layout.addWidget(self.validation)
        self.add_button.clicked.connect(self.add_rule)
        self.duplicate_button.clicked.connect(self.duplicate_rule)
        self.delete_button.clicked.connect(self.delete_rule)
        self.table.currentCellChanged.connect(self._selection_changed)
        self.table.cellDoubleClicked.connect(self._toggle_enabled)
        self.editor.textChanged.connect(self._editor_changed)
        self.name_editor.editingFinished.connect(self._name_changed)
        self.description_editor.textChanged.connect(self._description_changed)

    def set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.results = [(None, "") for _ in project.rules]
        self.refresh()

    def set_results(self, results: list[tuple[bool | None, str]]) -> None:
        self.results = results
        self.refresh(keep_selection=True)

    def refresh(self, keep_selection: bool = False) -> None:
        selected = self.table.currentRow() if keep_selection else -1
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        status_colors = {
            "true": "#68e0a0" if dark else "#198754",
            "false": "#ff8b85" if dark else "#c0392b",
            "error": "#ffd071" if dark else "#b7791f",
        }
        self._updating = True
        self.table.setRowCount(0)
        if self.project:
            for index, rule in enumerate(self.project.rules):
                row = self.table.rowCount()
                self.table.insertRow(row)
                result, error = self.results[index] if index < len(self.results) else (None, "")
                status = "ERROR" if error else ("TRUE" if result else "FALSE") if result is not None else "—"
                values = ["✓" if rule.enabled else "", rule.name, rule.expression, status, rule.source]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    if column == 3:
                        item.setForeground(QColor(status_colors["true"] if result else status_colors["false"] if result is False else status_colors["error"]))
                    self.table.setItem(row, column, item)
        self._updating = False
        if selected >= 0 and self.table.rowCount():
            self.table.selectRow(min(selected, self.table.rowCount() - 1))

    def add_rule(self) -> None:
        if not self.project:
            return
        index = len(self.project.rules) + 1
        self.project.rules.append(RuleModel(f"Manual Rule {index}", "TRUE"))
        self.results.append((None, ""))
        self.project.dirty = True
        self.refresh()
        self.table.selectRow(len(self.project.rules) - 1)
        self.rules_changed.emit()

    def duplicate_rule(self) -> None:
        if not self.project or self.table.currentRow() < 0:
            return
        source = self.project.rules[self.table.currentRow()]
        self.project.rules.append(RuleModel(f"{source.name} Copy", source.expression, "Manual", source.description))
        self.results.append((None, ""))
        self.project.dirty = True
        self.refresh()
        self.rules_changed.emit()

    def delete_rule(self) -> None:
        if not self.project or self.table.currentRow() < 0:
            return
        row = self.table.currentRow()
        del self.project.rules[row]
        if row < len(self.results):
            del self.results[row]
        self.project.dirty = True
        self.refresh()
        self.rules_changed.emit()

    def _toggle_enabled(self, row: int, column: int) -> None:
        if column != 0 or not self.project:
            return
        self.project.rules[row].enabled = not self.project.rules[row].enabled
        self.project.dirty = True
        self.refresh(keep_selection=True)
        self.rules_changed.emit()

    def _selection_changed(self, row: int, _column: int, _old_row: int, _old_column: int) -> None:
        self._updating = True
        if self.project and 0 <= row < len(self.project.rules):
            rule = self.project.rules[row]
            self.name_editor.setText(rule.name)
            self.description_editor.setText(rule.description)
            self.editor.setPlainText(rule.expression)
            self.rule_selected.emit(row)
        else:
            self.name_editor.clear()
            self.description_editor.clear()
            self.editor.clear()
        self._updating = False

    def _editor_changed(self) -> None:
        if self._updating or not self.project or self.table.currentRow() < 0:
            return
        self.project.rules[self.table.currentRow()].expression = self.editor.toPlainText().strip()
        self.project.dirty = True
        self.rules_changed.emit()

    def _name_changed(self) -> None:
        if self._updating or not self.project or self.table.currentRow() < 0:
            return
        row = self.table.currentRow()
        new_name = self.name_editor.text().strip()
        duplicate = any(index != row and rule.name.casefold() == new_name.casefold() for index, rule in enumerate(self.project.rules))
        if not new_name or duplicate:
            self._updating = True
            self.name_editor.setText(self.project.rules[row].name)
            self._updating = False
            self.set_validation("Rule names must be unique and non-empty", False)
            return
        self.project.rules[row].name = new_name
        self.project.dirty = True
        self.rules_changed.emit()

    def _description_changed(self, text: str) -> None:
        if self._updating or not self.project or self.table.currentRow() < 0:
            return
        self.project.rules[self.table.currentRow()].description = text
        self.project.dirty = True
        self.rules_changed.emit()

    def set_validation(self, text: str, valid: bool) -> None:
        self.validation.setText(text)
        self.validation.setStyleSheet(f"color: {'#198754' if valid else '#c0392b'};")


class DebugPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("EVALUATION / DEBUG")
        title.setStyleSheet("font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(title)
        self.badge = QLabel("NO RULE SELECTED")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setObjectName("errorBadge")
        layout.addWidget(self.badge)
        self.tabs = QTabWidget()
        self.explanation = QPlainTextEdit()
        self.explanation.setReadOnly(True)
        self.ast = QPlainTextEdit()
        self.ast.setReadOnly(True)
        self.relationships = QPlainTextEdit()
        self.relationships.setReadOnly(True)
        self.tabs.addTab(self.explanation, "Why?")
        self.tabs.addTab(self.ast, "Parser / AST")
        self.tabs.addTab(self.relationships, "Relationships")
        layout.addWidget(self.tabs, 1)
        self.interpretation = QLabel("Imported coordinate helpers are a transparent tester interpretation; verify critical behavior in OpenRoads.")
        self.interpretation.setWordWrap(True)
        self.interpretation.setStyleSheet("color: #64727e; font-style: italic;")
        layout.addWidget(self.interpretation)

    def show_result(self, value: bool, explanation: str, ast: str, relationships: str = "") -> None:
        self.badge.setText("TRUE" if value else "FALSE")
        self.badge.setObjectName("trueBadge" if value else "falseBadge")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        self.explanation.setPlainText(explanation)
        self.ast.setPlainText(ast)
        self.relationships.setPlainText(relationships or "No supported relationships are recorded for this rule.")

    def show_error(self, message: str, ast: str = "", relationships: str = "") -> None:
        self.badge.setText("SYNTAX / INPUT ERROR")
        self.badge.setObjectName("errorBadge")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        self.explanation.setPlainText(message)
        self.ast.setPlainText(ast)
        self.relationships.setPlainText(relationships)

    def show_object_details(self, title: str, details: str) -> None:
        self.badge.setText(title)
        self.badge.setObjectName("errorBadge")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        self.relationships.setPlainText(details)
        self.tabs.setCurrentWidget(self.relationships)
