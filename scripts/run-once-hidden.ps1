$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = Join-Path $root 'src'

$managedBin = Join-Path $root 'tools\bin'
if (Test-Path (Join-Path $managedBin 'rojo.exe')) {
    $env:PATH = $managedBin + ';' + $env:PATH
}

foreach ($gitDir in @('C:\Program Files\Git\cmd', 'C:\Program Files\Git\bin', (Join-Path $HOME 'AppData\Local\Programs\Git\cmd'))) {
    if (Test-Path (Join-Path $gitDir 'git.exe')) {
        $env:PATH = $gitDir + ';' + $env:PATH
        break
    }
}

python -m factory.runner --products products --work-root work/repos --state-root state
