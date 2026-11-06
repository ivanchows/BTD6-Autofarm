# Updates the farm to the newest version on GitHub. Keeps your stats and settings.
# Autofarm.exe runs this on every launch: it asks GitHub for the newest version first and only
# downloads when there is one, so most launches cost one small request.
# Exit codes: 0 = already up to date, 2 = updated, 1 = couldn't check or update.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot                          # the farm folder
$root = Split-Path $here -Parent               # the download's top folder (Autofarm.exe, Install.bat)
Set-Location $here
$repo = "ivanchows/BTD6-Autofarm"
$versionFile = Join-Path $here ".version"      # the commit this folder was last updated to

# Downloaded with git: just pull
if ((Test-Path (Join-Path $root ".git")) -and (Get-Command git -ErrorAction SilentlyContinue)) {
    $before = git -C $root rev-parse HEAD
    git -C $root pull --ff-only -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "git pull failed (files changed here?). Nothing was updated."
        exit 1
    }
    if ((git -C $root rev-parse HEAD) -ne $before) { Write-Host "Updated."; exit 2 }
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

# A newer version: fetch exactly that commit's zip and copy it over the download's folder
$tmp = Join-Path $env:TEMP ("btd6farm_update_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    Write-Host "Downloading the newest version..."
    $zip = Join-Path $tmp "update.zip"
    Invoke-WebRequest -Uri "https://github.com/$repo/archive/$sha.zip" -OutFile $zip -UseBasicParsing -TimeoutSec 120
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $src = Get-ChildItem -Path $tmp -Directory | Select-Object -First 1
    if (-not $src -or -not (Test-Path (Join-Path $src.FullName "farm\watchdog.py"))) {
        Write-Host "The download looks wrong. Nothing was updated."
        exit 1
    }
    # Your own files stay as they are (settings.json holds your keybinds). Autofarm.exe is running,
    # so it is swapped in by name below.
    $keepFiles = @("state.json", "state.json.tmp", "overlay_pos.json", "bonus_map.txt", "settings.json",
                   "gui.json", "skipped_maps.json", "glacial_progress.json", "glacial_prices.json",
                   "*.log", "*.log.old", ".version", "Autofarm.exe", "Autofarm.exe.old")
    $keepDirs = @("losses", "featured", "__pycache__", ".venv")
    robocopy $src.FullName $root /E /NFL /NDL /NJH /NJS /NP /XF $keepFiles /XD $keepDirs | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Write-Host "Copying failed (is the farm still running? Stop it and try again)."
        exit 1
    }
    # A new Autofarm.exe: the running one can't be overwritten, but it can be renamed
    $newExe = Join-Path $src.FullName "Autofarm.exe"
    $exe = Join-Path $root "Autofarm.exe"
    if ((Test-Path $newExe) -and (-not (Test-Path $exe) -or
            (Get-FileHash $newExe).Hash -ne (Get-FileHash $exe).Hash)) {
        Remove-Item "$exe.old" -Force -ErrorAction SilentlyContinue
        if (Test-Path $exe) { Rename-Item $exe "Autofarm.exe.old" }
        Copy-Item $newExe $exe
    }
    # From the old layout (everything at the top): carry the player's files into farm\, then
    # remove the old copies of the code so only Autofarm.exe, Install.bat and farm\ are left
    foreach ($f in @("state.json", "settings.json", "overlay_pos.json", "bonus_map.txt", "skipped_maps.json",
                     "farm.log", "watchdog.log", "losses", "featured", "maps\glacial_progress.json")) {
        $old = Join-Path $root $f
        if (Test-Path $old) {
            $to = Join-Path $here $f
            if (Test-Path $old -PathType Container) { robocopy $old $to /E /MOVE /NFL /NDL /NJH /NJS /NP | Out-Null }
            else { Move-Item $old $to -Force }
        }
    }
    foreach ($f in @("core.py", "watchdog.py", "gui.py", "keys.py", "capture_spots.py", "price_scan.py",
                     "heroes.json", "prices.json", "tower_costs.json", "updater.ps1", "Play.bat",
                     "Updater.bat", "Autofarm.bat", "state.json.tmp", "maps", "assets", "launcher", "__pycache__")) {
        $old = Join-Path $root $f
        if ((Test-Path $old) -and (Test-Path (Join-Path $here $f))) { Remove-Item $old -Recurse -Force }
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
