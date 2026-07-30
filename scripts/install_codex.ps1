$ErrorActionPreference = "Stop"
$ScriptPath = Join-Path $PSScriptRoot "install_codex.py"

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python $ScriptPath @args
    exit $LASTEXITCODE
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $ScriptPath @args
    exit $LASTEXITCODE
}

throw "Python 3 was not found. Install Python 3 and run this script again."
