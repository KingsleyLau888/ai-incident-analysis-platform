param(
    [switch]$Apply
)

$root = (Resolve-Path "$PSScriptRoot\..").Path

$files = @(
    "*.log",
    "*-journal",
    "auto_demo.db",
    "sqlite_probe.db",
    "sqlite_probe.db-journal"
)

$directories = @(
    ".demo_runtime",
    ".pytest_cache"
)

Write-Host "Project root: $root"
if (-not $Apply) {
    Write-Host "Dry run only. Re-run with -Apply to delete these runtime files."
}

$seenFiles = @{}
foreach ($pattern in $files) {
    Get-ChildItem -LiteralPath $root -Force -File -Filter $pattern | ForEach-Object {
        if ($_.FullName.StartsWith($root) -and -not $seenFiles.ContainsKey($_.FullName)) {
            $seenFiles[$_.FullName] = $true
            if ($Apply) {
                Remove-Item -LiteralPath $_.FullName -Force
                Write-Host "Deleted file: $($_.Name)"
            } else {
                Write-Host "Would delete file: $($_.Name)"
            }
        }
    }
}

foreach ($name in $directories) {
    $path = Join-Path $root $name
    if (Test-Path -LiteralPath $path) {
        $resolved = (Resolve-Path -LiteralPath $path).Path
        if ($resolved.StartsWith($root)) {
            if ($Apply) {
                Remove-Item -LiteralPath $resolved -Recurse -Force
                Write-Host "Deleted directory: $name"
            } else {
                Write-Host "Would delete directory: $name"
            }
        }
    }
}

Write-Host ""
Write-Host "Not deleted by this script:"
Write-Host "- incident-live.db"
Write-Host "- app.db"
Write-Host "- demo_shop.db"
Write-Host "- runtime/data/*.db"
Write-Host "- .chroma_db"
Write-Host "Delete those only when you intentionally want to reset local demo data."
