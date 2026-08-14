$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$entry = Join-Path $root 'scripts\daemon_entry.py'
$python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $python) { throw 'python.exe not found' }
$pythonw = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
if (-not (Test-Path $pythonw)) { throw 'pythonw.exe not found next to python.exe' }

$vbs = Join-Path $root 'scripts\run-factory-hidden.vbs'
$escapedPythonw = $pythonw.Replace('"', '""')
$escapedEntry = $entry.Replace('"', '""')
@"
Set shell = CreateObject("WScript.Shell")
cmd = Chr(34) & "$escapedPythonw" & Chr(34) & " " & Chr(34) & "$escapedEntry" & Chr(34)
shell.Run cmd, 0, False
"@ | Set-Content -Encoding ASCII $vbs

$taskName = 'RobloxAutonomousProductFactory'
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\wscript.exe" -Argument ('"' + $vbs + '"')
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30)
$settings = New-ScheduledTaskSettingsSet -Hidden -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Build, QA and release-gate Roblox products without visible consoles.' -Force | Out-Null
Write-Output "TASK=$taskName"
Write-Output "VBS=$vbs"
