"""Overnight watchdog for the farms (infernal_easy.py by default).

Keeps the PC and screen awake, and restarts the farm whenever it:
  - exits or crashes (anything but a Numpad 0 / F8 stop),
  - stops writing its heartbeat for 2 minutes (frozen),
  - goes 30 minutes without placing towers, winning or losing (stuck on some screen).
For the last two BTD6 is killed too, and the farm relaunches it through Steam.

Run:  uv run watchdog.py [quad_easy.py]        Stop: Numpad 0 (stops the farm and the watchdog).
"""
import ctypes
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "state.json")
FARM_LOG = os.path.join(HERE, "farm.log")
LOG = os.path.join(HERE, "watchdog.log")
import keys
STOP_KEYS = keys.load("stop")    # settings.json, plus Numpad 0 / Insert / F8
HEARTBEAT_LIMIT = 120
PROGRESS_LIMIT = 30 * 60
ARGS = [a for a in sys.argv[1:] if a.lower() != "afk"]
AFK = len(ARGS) < len(sys.argv) - 1     # `watchdog.py <map> afk`: tab back into BTD6 by itself
SCRIPT = ARGS[0] if ARGS else "infernal_easy.py"   # or any map script, or "bonus"
MAX_IMPOP_LOSSES = None   # user: stay on Impoppable (set a number to fall back to Deflation)
IMPOP_WIN_DEADLINE = None      # user: no time-based switch either

user32 = ctypes.windll.user32
ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x1 | 0x2)  # CONTINUOUS|SYSTEM|DISPLAY


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None             # mid-write or locked: unknown, not "frozen"


def stop_pressed():
    # 0x8001: held now, or pressed at any point since the last poll
    return any(user32.GetAsyncKeyState(k) & 0x8001 for k in STOP_KEYS)


# `watchdog.py bonus`: play whichever Expert map has the Collection Event's bonus rewards.
# The farm reads the bonus map off the event screen; if it isn't its own map, it writes the
# name to bonus_map.txt and exits, and the next start picks that map's farm.
BONUS_SCRIPTS = {
    "Infernal": "infernal_easy.py", "Flooded Valley": "flooded_easy.py",
    "Sanctuary": "sanctuary_deflation.py", "Ravine": "ravine_deflation.py",
    "Quad": "quad_easy.py", "Workshop": "workshop_easy.py", "Dark Dungeons": "dark_dungeons_easy.py",
    "Bloody Puddles": "bloody_puddles_easy.py", "Tricky Tracks": "tricky_tracks_easy.py",
    "#Ouch": "ouch_easy.py", "Dark Castle": "dark_castle_impop.py",
    "Muddy Puddles": "muddy_puddles_impop.py", "Glacial Trail": "glacial_trail_impop.py",
}
BONUS = SCRIPT.lower() == "bonus"

# A map or hero the player hasn't unlocked: the farm notes it in skipped_maps.json and exits 5.
# Bonus mode then plays one game on a map the player has (no-hero maps first) and checks the
# bonus again (the farm exits 6 after that win); one picked map stops with the reason.
SKIP_FILE = os.path.join(HERE, "skipped_maps.json")
SKIP_FOR = 6 * 3600
STAND_INS = ["infernal_easy.py", "flooded_easy.py", "bloody_puddles_easy.py", "ouch_easy.py",
             "quad_easy.py", "workshop_easy.py", "dark_dungeons_easy.py", "tricky_tracks_easy.py",
             "ravine_deflation.py", "sanctuary_deflation.py"]
SCRIPT_MAP = {v: k for k, v in BONUS_SCRIPTS.items()}
SCRIPT_MAP.update({"ravine_deflation.py": "Ravine", "sanctuary_deflation.py": "Sanctuary",
                   "sanctuary_impop.py": "Sanctuary", "infernal_impop.py": "Infernal"})
STAND_IN = {"script": None}


def skipped():
    try:
        d = json.load(open(SKIP_FILE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {m: v["why"] for m, v in d.items() if time.time() - v.get("t", 0) < SKIP_FOR}


def stand_in():
    """The first stand-in map the player can play, or None."""
    bad = skipped()
    for s in STAND_INS:
        if SCRIPT_MAP.get(s) not in bad:
            return s
    return None


def bonus_script():
    try:
        with open(os.path.join(HERE, "bonus_map.txt"), encoding="utf-8") as f:
            return BONUS_SCRIPTS.get(f.read().strip(), "quad_easy.py")
    except OSError:
        return "quad_easy.py"           # any farm: it checks the event and switches if needed


def start_farm(extra=()):
    st = state() or {}
    if BONUS:
        globals()["SCRIPT"] = STAND_IN["script"] or bonus_script()
    path = os.path.join(HERE, "maps", os.path.basename(SCRIPT))     # map scripts live in maps/
    if not os.path.exists(path):
        path = os.path.join(HERE, SCRIPT)
    args = ["uv", "run", "-q", path, *extra]
    fresh = time.time() - st.get("heartbeat", 0) < HEARTBEAT_LIMIT
    if fresh and st.get("running") and user32.FindWindowW(None, "BloonsTD6"):
        args.append("--running")        # towers are already down in this game
    log("starting farm " + " ".join(args[3:]))
    out = open(FARM_LOG, "a", encoding="utf-8")
    env = dict(os.environ, PYTHONUNBUFFERED="1", **({"BTD6_AFK": "1"} if AFK else {}))
    if BONUS and STAND_IN["script"]:
        env["BTD6_ONE_GAME"] = "1"      # one game on a stand-in map, then back to the bonus
    elif BONUS:
        env["BTD6_BONUS"] = "1"
    return subprocess.Popen(args, cwd=HERE, stdout=out, stderr=subprocess.STDOUT, env=env,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)


def kill(proc):
    subprocess.run(["taskkill", "/f", "/t", "/pid", str(proc.pid)], capture_output=True)


WATCH_START = time.time()


def main():
    log("watchdog up" + (" (AFK mode: tabs back into BTD6)" if AFK else ""))
    try:                                # a stop from the last session must not end this one
        st = state() or {}
        st.setdefault("stats", {}).pop("stopped", None)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f)
    except OSError:
        pass
    stop_pressed()                      # clear any old "pressed since" bit
    proc = start_farm()
    started = time.time()
    while True:
        hit = False
        for _ in range(10):             # check the stop key every 0.2 s (reading clears the
            time.sleep(0.2)             # "pressed since" bit, so keep the result)
            if stop_pressed():
                hit = True
                break
        if hit:
            kill(proc)
            log("stopped by hotkey")
            return
        code = proc.poll()
        if code is not None:
            if (state() or {}).get("stats", {}).get("stopped"):
                log("farm stopped by hotkey, watchdog exiting")
                return
            if code == 5:               # map or hero not unlocked
                why = skipped()
                name = SCRIPT_MAP.get(os.path.basename(SCRIPT), SCRIPT)
                if not BONUS:
                    log(f"can't play {name}: {why.get(name, 'not unlocked')}. Unlock it, or pick another map.")
                    return
                STAND_IN["script"] = stand_in()
                if STAND_IN["script"] is None:
                    log("none of the maps can be played (maps or heroes not unlocked): stopping")
                    return
                log(f"{name} skipped ({why.get(name, 'not unlocked')}): one game on "
                    f"{SCRIPT_MAP.get(STAND_IN['script'], STAND_IN['script'])} meanwhile")
            elif code == 6:             # the stand-in game is won: check the bonus map again
                STAND_IN["script"] = None
                log("stand-in game done, back to the bonus map")
            else:
                log(f"farm exited ({code}), restarting")
        else:
            if time.time() - started < 90:      # give it time to boot / relaunch the game
                continue
            st = state()
            if st is None:
                continue
            stats = st.get("stats", {})
            too_slow = (IMPOP_WIN_DEADLINE is not None and stats.get("wins", 0) == 0
                        and time.time() - WATCH_START > IMPOP_WIN_DEADLINE)
            too_many = MAX_IMPOP_LOSSES is not None and stats.get("losses", 0) >= MAX_IMPOP_LOSSES
            if SCRIPT == "infernal_impop.py" and (too_many or too_slow):
                log("no Impoppable win in 90 min" if too_slow else f"{MAX_IMPOP_LOSSES} Impoppable losses"
                    + ": switching to the Deflation farm")
                kill(proc)
                globals()["SCRIPT"] = "infernal_easy.py"
                time.sleep(3)
                proc = start_farm(["--go-home"])
                started = time.time()
                continue
            beat = time.time() - st.get("heartbeat", 0)
            progress = time.time() - max(st.get("stats", {}).get("progress", 0), started)
            if beat > HEARTBEAT_LIMIT or progress > PROGRESS_LIMIT:
                why = (f"no heartbeat for {beat:.0f}s" if beat > HEARTBEAT_LIMIT
                       else f"no progress for {progress / 60:.0f} min")
                log(why + ", restarting farm and BTD6")   # fresh game, no half-placed towers
                kill(proc)
                subprocess.run(["taskkill", "/f", "/im", "BloonsTD6.exe"], capture_output=True)
                time.sleep(5)
            else:
                continue
        time.sleep(5)
        proc = start_farm()
        started = time.time()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"watchdog crashed: {e!r}")
        raise
