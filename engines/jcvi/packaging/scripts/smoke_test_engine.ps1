param(
  [string]$EngineExe
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $EngineExe)) {
  throw "Engine exe not found: $EngineExe"
}
& $EngineExe probe --json
