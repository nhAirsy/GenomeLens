param(
  [string]$RuntimeExe
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $RuntimeExe)) {
  throw "Runtime exe not found: $RuntimeExe"
}
& $RuntimeExe --version
& $RuntimeExe --help
