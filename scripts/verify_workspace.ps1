$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
Push-Location "$root\platform"
python -m pytest
Pop-Location
Push-Location "$root\engines\jcvi"
python -m pytest
Pop-Location
$env:PYTHONPATH = "$root\integrations\haiant_plugin\src"
python -m pytest "$root\integrations\haiant_plugin\tests"
Write-Host "Workspace verification completed."
