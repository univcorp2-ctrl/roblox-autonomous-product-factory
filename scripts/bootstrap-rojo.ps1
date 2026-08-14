$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $root 'tools\bin'
$zip = Join-Path $env:TEMP 'rojo-7.6.1-windows-x86_64.zip'
$uri = 'https://github.com/rojo-rbx/rojo/releases/download/v7.6.1/rojo-7.6.1-windows-x86_64.zip'

New-Item -ItemType Directory -Force -Path $bin | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $zip
Expand-Archive -Force -Path $zip -DestinationPath $bin
$rojo = Join-Path $bin 'rojo.exe'
if (-not (Test-Path $rojo)) { throw 'Pinned Rojo binary was not extracted' }
$version = & $rojo --version
if ($LASTEXITCODE -ne 0 -or $version -notmatch '7\.6\.1') { throw "Unexpected Rojo version: $version" }
Write-Output $version
