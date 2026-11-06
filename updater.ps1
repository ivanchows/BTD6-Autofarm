# Updates the farm to the newest version on GitHub. Keeps your stats and settings.
# Autofarm.exe runs this on every launch: it asks GitHub for the newest version first and only
# downloads when there is one, so most launches cost one small request.
# Exit codes: 0 = already up to date, 2 = updated, 1 = couldn't check or update.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
Set-Location $here
$repo = "ivanchows/BTD6-Autofarm"
$versionFile = Join-Path $here ".version"      # the commit this folder was last updated to

# Downloaded with git: just pull
if ((Test-Path (Join-Path $here ".git")) -and (Get-Command git -ErrorAction SilentlyContinue)) {
    $before = git rev-parse HEAD
    git pull --ff-only -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "git pull failed (files changed here?). Nothing was updated."
        exit 1
    }
    if ((git rev-parse HEAD) -ne $before) { Write-Host "Updated."; exit 2 }
    Write-Host "Up to date."
    exit 0
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
try {
    # The newest commit on main: one small request, answered as plain text
    $sha = (Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/commits/main" -TimeoutSec 10 `
            -Headers @{ Accept = "application/vnd.github.sha"; "User-Agent" = "BTD6-Autofarm-updater" }).Trim()
} catch {
    Write-Host "Couldn't check for updates (offline?)."
    exit 1
}
$have = if (Test-Path $versionFile) { (Get-Content $versionFile -Raw).Trim() } else { "" }
if ($sha -and $sha -eq $have) {
    Write-Host "Up to date."
    exit 0
}

# A newer version: fetch exactly that commit's zip and copy it over this folder
$tmp = Join-Path $env:TEMP ("btd6farm_update_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    Write-Host "Downloading the newest version..."
    $zip = Join-Path $tmp "update.zip"
    Invoke-WebRequest -Uri "https://github.com/$repo/archive/$sha.zip" -OutFile $zip -UseBasicParsing -TimeoutSec 120
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $src = Get-ChildItem -Path $tmp -Directory | Select-Object -First 1
    if (-not $src -or -not (Test-Path (Join-Path $src.FullName "watchdog.py"))) {
        Write-Host "The download looks wrong. Nothing was updated."
        exit 1
    }
    # Your own files stay as they are (settings.json holds your keybinds). Autofarm.exe is
    # running while this runs, so it can't be replaced now.
    $keepFiles = @("state.json", "state.json.tmp", "overlay_pos.json", "bonus_map.txt", "settings.json",
                   "gui.json", "skipped_maps.json", "glacial_progress.json", "glacial_prices.json",
                   "*.log", "*.log.old", ".version", "Autofarm.exe")
    $keepDirs = @("losses", "featured", "__pycache__", ".venv")
    robocopy $src.FullName $here /E /NFL /NDL /NJH /NJS /NP /XF $keepFiles /XD $keepDirs | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Write-Host "Copying failed (is the farm still running? Stop it and try again)."
        exit 1
    }
    Set-Content -Path $versionFile -Value $sha -NoNewline
    Write-Host "Updated. Your stats and settings were kept."
    exit 2
} catch {
    Write-Host "Update failed: $($_.Exception.Message)"
    Write-Host "Check your internet and try again."
    exit 1
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
