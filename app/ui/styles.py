LIGHT_QSS = """
QMainWindow, QWidget { background: #f4f6f8; color: #202932; font-family: "Segoe UI"; font-size: 10pt; }
QMenuBar, QMenu, QToolBar, QStatusBar { background: #ffffff; }
QToolBar { border-bottom: 1px solid #d7dde3; spacing: 5px; padding: 5px; }
QGroupBox { background: #ffffff; border: 1px solid #d7dde3; border-radius: 7px; margin-top: 12px; padding-top: 9px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTableWidget, QTreeWidget, QListWidget {
  background: #ffffff; border: 1px solid #cbd3da; border-radius: 5px; padding: 4px; selection-background-color: #d8ebff; selection-color: #17222c;
}
QTableWidget, QTreeWidget, QListWidget { border-radius: 6px; gridline-color: #e4e8ec; alternate-background-color: #f3f6f8; }
QHeaderView::section { background: #eaf0f5; color: #344451; padding: 6px; border: 0; border-right: 1px solid #d7dde3; border-bottom: 1px solid #d7dde3; font-weight: 600; }
QPushButton, QToolButton { background: #ffffff; border: 1px solid #bfc9d2; border-radius: 5px; padding: 5px 10px; }
QPushButton:hover, QToolButton:hover { background: #edf5fc; border-color: #6ca5d4; }
QPushButton:pressed { background: #dcecf9; }
QPushButton#accent { background: #1769aa; color: white; border-color: #1769aa; font-weight: 600; }
QTabWidget::pane { background: #ffffff; border: 1px solid #d7dde3; border-radius: 6px; }
QTabBar::tab { background: #e8edf1; padding: 7px 12px; margin-right: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px; }
QTabBar::tab:selected { background: #ffffff; color: #1769aa; font-weight: 600; }
QSplitter::handle { background: #dce2e7; width: 2px; height: 2px; }
QLabel#trueBadge { background: #d9f3e4; color: #106b3d; border: 1px solid #83cea3; border-radius: 6px; padding: 8px; font-size: 14pt; font-weight: 700; }
QLabel#falseBadge { background: #fde3e2; color: #a32b27; border: 1px solid #e6a09c; border-radius: 6px; padding: 8px; font-size: 14pt; font-weight: 700; }
QLabel#errorBadge { background: #fff0d4; color: #875b00; border: 1px solid #e0bd72; border-radius: 6px; padding: 8px; font-weight: 600; }
"""

DARK_QSS = """
QMainWindow, QWidget { background: #20252b; color: #e5ebf0; font-family: "Segoe UI"; font-size: 10pt; }
QMenuBar, QMenu, QToolBar, QStatusBar { background: #292f36; color: #e5ebf0; }
QToolBar { border-bottom: 1px solid #3c444d; spacing: 5px; padding: 5px; }
QGroupBox { background: #292f36; border: 1px solid #414a54; border-radius: 7px; margin-top: 12px; padding-top: 9px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTableWidget, QTreeWidget, QListWidget {
  background: #181c20; color: #eef3f7; border: 1px solid #46515c; border-radius: 5px; padding: 4px; selection-background-color: #285f8f;
}
QTableWidget, QTreeWidget, QListWidget { border-radius: 6px; gridline-color: #353d45; alternate-background-color: #1d2227; }
QHeaderView::section { background: #343c45; color: #e8edf1; padding: 6px; border: 0; border-right: 1px solid #46515c; border-bottom: 1px solid #46515c; font-weight: 600; }
QPushButton, QToolButton { background: #343c45; color: #eef3f7; border: 1px solid #53606c; border-radius: 5px; padding: 5px 10px; }
QPushButton:hover, QToolButton:hover { background: #40505e; border-color: #62a0d2; }
QPushButton#accent { background: #2580c5; color: white; border-color: #2580c5; font-weight: 600; }
QTabWidget::pane { background: #292f36; border: 1px solid #414a54; border-radius: 6px; }
QTabBar::tab { background: #343c45; padding: 7px 12px; margin-right: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px; }
QTabBar::tab:selected { background: #292f36; color: #70b7ee; font-weight: 600; }
QSplitter::handle { background: #414a54; width: 2px; height: 2px; }
QLabel#trueBadge { background: #173e2a; color: #7ee0aa; border: 1px solid #287a4e; border-radius: 6px; padding: 8px; font-size: 14pt; font-weight: 700; }
QLabel#falseBadge { background: #4a2527; color: #ffaaa5; border: 1px solid #914246; border-radius: 6px; padding: 8px; font-size: 14pt; font-weight: 700; }
QLabel#errorBadge { background: #4b3d20; color: #ffd37c; border: 1px solid #84672c; border-radius: 6px; padding: 8px; font-weight: 600; }
"""
