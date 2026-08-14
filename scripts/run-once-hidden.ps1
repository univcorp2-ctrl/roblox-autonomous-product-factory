$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = Join-Path $root 'src'
python -m factory.runner --products products --work-root work/repos --state-root state
