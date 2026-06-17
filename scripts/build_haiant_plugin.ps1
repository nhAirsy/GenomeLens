$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$pluginName = "GenomeLens-HAIant-plugin-1.0.0"
$stage = Join-Path $root ".build\$pluginName"
$zip = Join-Path $root "app\$pluginName.zip"
if (Test-Path $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
if (-not (Test-Path "$root\integrations\haiant_plugin\dist\GenomeLens.exe")) {
  throw "Plugin entry exe not found. Build integrations/haiant_plugin first."
}
Copy-Item "$root\integrations\haiant_plugin\dist\GenomeLens.exe" "$stage\GenomeLens.exe" -Force
Copy-Item "$root\integrations\haiant_plugin\assets\config.json" "$stage\config.json"
Copy-Item "$root\integrations\haiant_plugin\assets\params.json" "$stage\params.json"
Copy-Item "$root\integrations\haiant_plugin\assets\README.md" "$stage\README.md"
Copy-Item "$root\integrations\haiant_plugin\PARAMETER_MAPPING.md" "$stage\PARAMETER_MAPPING.md"
New-Item -ItemType Directory -Force -Path "$stage\input" | Out-Null
Copy-Item "$root\references\samples\shell\bed_cds_minimal\query.bed" "$stage\input\query.bed" -Force
Copy-Item "$root\references\samples\shell\bed_cds_minimal\query.cds" "$stage\input\query.cds" -Force
Copy-Item "$root\references\samples\shell\bed_cds_minimal\subject.bed" "$stage\input\subject.bed" -Force
Copy-Item "$root\references\samples\shell\bed_cds_minimal\subject.cds" "$stage\input\subject.cds" -Force
New-Item -ItemType Directory -Force -Path "$stage\output" | Out-Null
New-Item -ItemType Directory -Force -Path "$stage\runtime\GenomeLens" | Out-Null
if (Test-Path "$root\platform\dist\GenomeLens") {
  Copy-Item "$root\platform\dist\GenomeLens\*" "$stage\runtime\GenomeLens" -Recurse -Force
}
if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path "$stage\*" -DestinationPath $zip
Write-Host "Wrote $zip"
