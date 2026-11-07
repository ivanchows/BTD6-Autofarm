"""Updates the farm to the newest version on GitHub. Keeps your stats and settings.

The app runs this when it opens: it asks GitHub for the newest version first and only downloads when
there is one, so most launches cost one small request. Plain Python on purpose: no PowerShell.

    python updater.py      exit 0 = already up to date, 2 = updated, 1 = couldn't check or update
"""
import fnmatch
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))     # the farm folder
ROOT = os.path.dirname(HERE)                          # the download's top folder (Autofarm.exe, Install.bat)
REPO = "ivanchows/BTD6-Autofarm"
VERSION_FILE = os.path.join(HERE, ".version")         # the commit this folder was last updated to
AGENT = {"User-Agent": "BTD6-Autofarm-updater"}
NO_WINDOW = 0x08000000

# Your own files stay as they are (settings.json holds your keybinds)
KEEP_FILES = ["state.json", "state.json.tmp", "overlay_pos.json", "bonus_map.txt", "settings.json", "gui.json",
              "skipped_maps.json", "glacial_progress.json", "glacial_prices.json", "*.log", "*.log.old",
              ".version", "Autofarm.exe", "Autofarm.exe.old"]
KEEP_DIRS = {"losses", "featured", "learned", "__pycache__", ".venv"}
# Left over from older versions
STALE = ["farm/updater.ps1"]
# The old layout (everything at the top): the player's files move into farm\, then the old code goes
OLD_USER = ["state.json", "settings.json", "overlay_pos.json", "bonus_map.txt", "skipped_maps.json",
            "farm.log", "watchdog.log", "losses", "featured", os.path.join("maps", "glacial_progress.json")]
OLD_CODE = ["core.py", "watchdog.py", "gui.py", "keys.py", "capture_spots.py", "price_scan.py", "heroes.json",
            "prices.json", "tower_costs.json", "updater.ps1", "Play.bat", "Updater.bat", "Autofarm.bat",
            "state.json.tmp", "maps", "assets", "launcher", "__pycache__"]


def _git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, creationflags=NO_WINDOW)


def _same(a, b):
    if os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, "rb") as f, open(b, "rb") as g:
        return f.read() == g.read()


def _copy_tree(src, dst):
    for d, dirs, files in os.walk(src):
        dirs[:] = [x for x in dirs if x not in KEEP_DIRS]
        to = os.path.join(dst, os.path.relpath(d, src))
        os.makedirs(to, exist_ok=True)
        for f in files:
            if not any(fnmatch.fnmatch(f.lower(), k.lower()) for k in KEEP_FILES):
                shutil.copy2(os.path.join(d, f), os.path.join(to, f))


def _swap_exe(src):
    """The exe may be open, so it can't be overwritten, but it can be renamed."""
    new, exe = os.path.join(src, "Autofarm.exe"), os.path.join(ROOT, "Autofarm.exe")
    if not os.path.exists(new) or (os.path.exists(exe) and _same(new, exe)):
        return
    try:
        os.remove(exe + ".old")
    except OSError:
        pass
    if os.path.exists(exe):
        os.replace(exe, exe + ".old")
    shutil.copy2(new, exe)


def _tidy():
    for f in STALE:
        try:
            os.remove(os.path.join(ROOT, f))
        except OSError:
            pass
    for f in OLD_USER:
        old, to = os.path.join(ROOT, f), os.path.join(HERE, f)
        if os.path.isdir(old):
            shutil.copytree(old, to, dirs_exist_ok=True)
            shutil.rmtree(old, ignore_errors=True)
        elif os.path.isfile(old):
            os.replace(old, to)
    for f in OLD_CODE:
        old = os.path.join(ROOT, f)
        if os.path.exists(old) and os.path.exists(os.path.join(HERE, f)):
            shutil.rmtree(old, ignore_errors=True) if os.path.isdir(old) else os.remove(old)


def check():
    """Is there a newer version? Downloads nothing. (code, message): 3 yes, 0 no, 1 couldn't check."""
    if os.path.isdir(os.path.join(ROOT, ".git")) and shutil.which("git"):
        if _git("fetch", "-q").returncode:
            return 1, "Couldn't check for updates (offline?)."
        n = _git("rev-list", "--count", "HEAD..@{u}").stdout.strip()
        return (3, "Update ready.") if n.isdigit() and int(n) > 0 else (0, "Up to date.")
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/commits/main",
                                     headers={**AGENT, "Accept": "application/vnd.github.sha"})
        sha = urllib.request.urlopen(req, timeout=10).read().decode().strip()
    except Exception:
        return 1, "Couldn't check for updates (offline?)."
    try:
        have = open(VERSION_FILE, encoding="utf-8").read().strip()
    except OSError:
        have = ""
    return (0, "Up to date.") if sha and sha == have else (3, "Update ready.")


def update():
    """Returns (code, message): 0 up to date, 2 updated, 1 couldn't."""
    if os.path.isdir(os.path.join(ROOT, ".git")) and shutil.which("git"):     # downloaded with git: just pull
        before = _git("rev-parse", "HEAD").stdout.strip()
        if _git("pull", "--ff-only", "-q").returncode:
            return 1, "git pull failed (files changed here?). Nothing was updated."
        return (2, "Updated.") if _git("rev-parse", "HEAD").stdout.strip() != before else (0, "Up to date.")
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/commits/main",
                                     headers={**AGENT, "Accept": "application/vnd.github.sha"})
        sha = urllib.request.urlopen(req, timeout=10).read().decode().strip()
    except Exception:
        return 1, "Couldn't check for updates (offline?)."
    try:
        have = open(VERSION_FILE, encoding="utf-8").read().strip()
    except OSError:
        have = ""
    if sha and sha == have:
        return 0, "Up to date."
    tmp = tempfile.mkdtemp(prefix="btd6farm_update_")
    try:
        z = os.path.join(tmp, "update.zip")
        req = urllib.request.Request(f"https://github.com/{REPO}/archive/{sha}.zip", headers=AGENT)
        with urllib.request.urlopen(req, timeout=120) as r, open(z, "wb") as f:
            shutil.copyfileobj(r, f)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(os.path.join(tmp, "x"))
        tops = os.listdir(os.path.join(tmp, "x"))
        src = os.path.join(tmp, "x", tops[0]) if len(tops) == 1 else ""
        if not os.path.isfile(os.path.join(src, "farm", "watchdog.py")):
            return 1, "The download looks wrong. Nothing was updated."
        _copy_tree(src, ROOT)
        _swap_exe(src)
        _tidy()
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(sha)
        return 2, "Updated. Your stats and settings were kept."
    except PermissionError:
        return 1, "Copying failed (is the farm still running? Stop it and try again)."
    except Exception as e:
        return 1, f"Update failed: {e}. Check your internet and try again."
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    code, msg = update()
    print(msg)
    sys.exit(code)
