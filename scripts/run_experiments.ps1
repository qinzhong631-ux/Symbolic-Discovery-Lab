param(
    [ValidateSet('smoke', 'quick', 'reference')]
    [string]$Profile = 'quick',
    [string[]]$Models = @(),
    [string]$Output = ''
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $ProjectRoot
$ProjectPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $ProjectPython)) { $ProjectPython = 'python' }
if (-not $Output) { $Output = 'runs/' + $Profile + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') }
$env:JULIA_DEPOT_PATH = Join-Path $ProjectRoot '.julia'
$env:PYTHON_JULIACALL_THREADS = '1'
$RunArguments = @('-m', 'symbolic_discovery', 'run', '--config', "configs/$Profile.json", '--output', $Output)
if ($Models.Count -gt 0) { $RunArguments += '--models'; $RunArguments += $Models }
& $ProjectPython @RunArguments
exit $LASTEXITCODE
