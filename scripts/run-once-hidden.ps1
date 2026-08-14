$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = Join-Path $root 'src'

# Prefer the factory-managed pinned Rojo binary when present so unattended
# execution does not depend on a user's interactive shell PATH.
$managedBin = Join-Path $root 'tools\bin'
if (Test-Path (Join-Path $managedBin 'rojo.exe')) {
    $env:PATH = $managedBin + ';' + $env:PATH
}

python -m factory.runner --products products --work-root work/repos --state-root state
