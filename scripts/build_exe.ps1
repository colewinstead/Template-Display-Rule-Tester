param(
    [string]$PythonPath = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$entryPoint = Join-Path $projectRoot "main.py"
$outputRoot = Join-Path $projectRoot "build-output"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python environment not found at $PythonPath. Create .venv and install requirements.txt first."
}

& $PythonPath -m PyInstaller --noconfirm --clean --windowed --name "Template Display Rule Tester" --distpath (Join-Path $outputRoot "dist") --workpath (Join-Path $outputRoot "work") --specpath $outputRoot $entryPoint
Write-Host "Executable created under $outputRoot\dist\Template Display Rule Tester"
