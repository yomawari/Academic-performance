param(
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = "py"
$pythonPrefix = @("-3")
if (Test-Path ".venv\Scripts\python.exe") {
    $python = ".venv\Scripts\python.exe"
    $pythonPrefix = @()
}

$uvicornArgs = $pythonPrefix + @("-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$Port")
if ($Reload) { $uvicornArgs += "--reload" }

Write-Host "Запуск «Учёт успеваемости» на http://127.0.0.1:$Port" -ForegroundColor Cyan
& $python @uvicornArgs
