# Template Display Rule Tester

A polished Windows desktop utility for inspecting Bentley OpenRoads/InRoads template libraries and debugging display-rule logic without changing production `.itl` files. It combines a real ITL explorer with a safe Boolean expression engine, visible AST and evaluation trace, interactive test coordinates, range and matrix tests, rule comparison, gap/overlap detection, scenarios, truth tables, diagnostics, and exports.

## ITL safety and sample findings

The local development sample `rwd.itl` is always opened read-only. It is deliberately excluded from Git because template libraries may contain organization-specific engineering data. Tester inputs are stored only in separate `.ordrule` JSON project files, which are also ignored by Git. The inspected sample is well-formed, uncompressed InRoads XML and exposes 216 templates, 5,889 points, 2,921 components, 1,027 display rules, and 11,778 constraints. See [ITL_INVESTIGATION.md](ITL_INVESTIGATION.md) for the hash, exact element inventory, supported relationships, and evidence-based limitations.

The current parser extracts the real category/template hierarchy, point names and coordinates, point constraints and parents, components and vertices, atomic display rules, and component `displayExpression` relationships. Unknown fields are tolerated and useful raw attributes are preserved in memory. The application never saves to an ITL.

## Install and run

Python 3.11 or newer is recommended. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

When a local `rwd.itl` is present beside the source, it loads automatically. Otherwise, use **File > Open ITL** to select a library. Double-click a display rule in the explorer to import its referenced point coordinates and tester expression.

The application launches in dark mode by default to sit comfortably beside an OpenRoads/CAD viewport. **View > Dark Mode** (`Ctrl+D`) can switch to the included light theme.

## Rule language

The parser is independent of the GUI and never calls Python `eval()`. It tokenizes input, creates an AST, and evaluates only supported nodes and whitelisted helper functions.

Supported comparisons are `<`, `>`, `<=`, `>=`, `=`, `==`, `!=`, and `<>`. Logical `AND`, `OR`, and `NOT` are case-insensitive; Boolean literals and nested parentheses are supported. `NOT GR_R < 1` and `NOT (GR_R < 1)` both parse as `NOT` applied to the comparison, which the AST tab makes explicit.

Imported Bentley atomic rules use visible helpers:

- `HDIFF(x1, x2)` / `AHDIFF(x1, x2)`
- `VDIFF(y1, y2)` / `AVDIFF(y1, y2)`
- `SLOPE(x1, y1, x2, y2)`

Syntax and unknown-variable errors are presented as friendly messages. Variable lookup is case-insensitive.
Bentley names containing spaces or punctuation are preserved with bracket notation, for example `[S/W Test.X]`; they are not sanitized or renamed.

## Testing

The test suite covers comparisons, negative/decimal/zero/Boolean values, precedence, parentheses, NOT interpretation, unknown variables, malformed syntax, explanations, helper functions, range/matrix/compare/conflict/truth tools, project round trips, and the real ITL fixture when it is available locally. Real-ITL tests skip cleanly in GitHub Actions because the private fixture is not committed.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests also run with the standard library:

```powershell
python -m unittest discover -v
```

## Build a Windows executable

After installing `requirements.txt`:

```powershell
.\scripts\build_exe.ps1
```

PyInstaller writes the standalone application under `build-output\dist`. The `.itl` sample is intentionally not embedded; users open their library read-only at runtime.

## Bentley behavior disclaimer

The ITL XML identifies rule operations and references but does not document all OpenRoads runtime details. The tester uses transparent ordinary numeric differences and rise-over-run slope. Bentley point-control resolution, runtime component order, tolerance behavior, and degenerate geometry may differ. The tool is a debugger and inspector, not a replacement for final verification in OpenRoads Designer.
