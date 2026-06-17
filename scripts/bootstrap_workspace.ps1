$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
Write-Host "GenomeLens workspace: $root"
python --version
foreach ($dir in @("platform", "engines/jcvi", "integrations", "references", "toolchains", "app", "docs")) {
  $path = Join-Path $root $dir
  if (-not (Test-Path $path)) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
  }
}
Write-Host "Workspace bootstrap complete."
