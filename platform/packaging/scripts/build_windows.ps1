param(
  [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
)

$ErrorActionPreference = "Stop"
Push-Location $ProjectRoot
python -m PyInstaller packaging\pyinstaller\genomelens.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Pop-Location
