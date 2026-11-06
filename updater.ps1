# Updates the farm to the newest version on GitHub. Keeps your stats and settings.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
Set-Location $here

# Downloaded with git: just pull
if ((Test-Path (Join-Path $here ".git")) -and (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Updating with git..."
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) {
        Write-Host "git pull failed (files changed here?). Nothing was updated."
        exit 1
    }
    Write-Host "Up to date."
    exit 0
}

# Downloaded as a zip: fetch the newest zip and copy it over this folder
$url = "https://github.com/ivanchows/BTD6-Autofarm/archive/refs/heads/main.zip"
$tmp = Join-Path $env:TEMP ("btd6farm_update_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    Write-Host "Downloading the newest version..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $zip = Join-Path $tmp "main.zip"
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $src = Get-ChildItem -Path $tmp -Directory | Select-Object -First 1
    if (-not $src -or -not (Test-Path (Join-Path $src.FullName "watchdog.py"))) {
        Write-Host "The download looks wrong. Nothing was updated."
        exit 1
    }
    # Your own files stay as they are
    $keepFiles = @("state.json", "state.json.tmp", "overlay_pos.json", "bonus_map.txt",
                   "skipped_maps.json", "glacial_progress.json", "glacial_prices.json", "*.log")
    $keepDirs = @("losses", "featured", "__pycache__", ".venv")
    robocopy $src.FullName $here /E /NFL /NDL /NJH /NJS /NP /XF $keepFiles /XD $keepDirs | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Write-Host "Copying failed (is the farm still running? Stop it and try again)."
        exit 1
    }
    Write-Host "Updated. Your stats and settings were kept."
    exit 0
} catch {
    Write-Host "Update failed: $($_.Exception.Message)"
    Write-Host "Check your internet and try again."
    exit 1
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
