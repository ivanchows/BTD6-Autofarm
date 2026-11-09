# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Infernal, Easy, Deflation.

Start it with the game on round 31 of a fresh Infernal Deflation game (nothing placed),
or on the victory screen. It places a 0-2-4 Sniper and a 4-0-2 Wizard, starts the game
at double speed, and restarts after every win.

A stats overlay (runs, XP, Monkey Money, uptime) sits over the game's top-left corner.
Pause/resume: Numpad 1.
Stop: press Numpad 0 (or F8), or slam the mouse into the top-left corner.
For overnight runs start watchdog.py instead: it restarts this script if it dies or stalls.
"""
import asyncio
import json
import ctypes
import ctypes.wintypes as wt
import os
import re
import sys
import threading
import time
import tkinter as tk

import mapsig
import pics
import mss
from PIL import Image, ImageOps

_print = print


def print(*args, **kw):     # timestamp every log line
    _print(time.strftime("%H:%M:%S"), *args, **kw)

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

# ---------------------------------------------------------------- config
# Positions are measured on a 1920x1080 window and scaled to the real one.
SNIPER_KEY = "z"
WIZARD_KEY = "a"
ALCH_KEY = "f"
UPGRADE_KEYS = {"top": ",", "mid": ".", "bot": "/"}

SNIPER_POS = (1560, 600)
WIZARD_POS = (835, 730)   # the cursor sits below the tower; 690 is off the rock
ALCH_POS = (1605, 650)    # beside the sniper, buffs it
SNIPER_PATH = (0, 2, 4)
WIZARD_PATH = (4, 0, 2)
ALCH_PATH = (2, 0, 0)

# Pixels that tell the screens apart: (x, y, (r, g, b), tolerance)
IN_GAME = [(1685, 62, (54, 207, 0), 40)]                       # green UPGRADES button
DEFLATION_POPUP = [(900, 740, (114, 232, 0), 40), (1020, 780, (59, 214, 0), 40),
                   (520, 480, (98, 151, 216), 40)]             # "Start at round 31" + OK
VICTORY_STATS = [(880, 880, (116, 232, 3), 40), (1040, 935, (53, 211, 0), 40),
                 (680, 140, (247, 117, 38), 40), (1240, 140, (247, 117, 38), 40)]   # Next + the banner's ends, not its word
VICTORY_MENU = [(1200, 820, (113, 232, 0), 40), (560, 460, (102, 153, 217), 40)]  # Home/Review/Freeplay
# yellow Restart + the blue panel (never a pixel on the DEFEAT banner: its word changes with the language)
DEFEAT = [(990, 840, (240, 185, 0), 40), (570, 500, (93, 145, 214), 40), (1340, 480, (94, 147, 215), 40)]
DEFEAT_PAID = [(880, 840, (250, 193, 0), 40), (570, 500, (93, 145, 214), 40), (1340, 480, (94, 147, 215), 40)]  # 4 buttons, last = paid Continue
RESTART_CONFIRM = [(1060, 710, (114, 232, 0), 40), (700, 710, (255, 221, 0), 40), (960, 380, (113, 232, 0), 40)]
EVENT = [(100, 500, (87, 61, 103), 30), (1700, 800, (86, 60, 102), 30),
         (700, 50, (118, 38, 163), 40)]                        # Halloween collection event
INSTA_REVEAL = [(960, 262, (255, 217, 0), 40), (700, 262, (153, 17, 18), 50)]  # "INSTA MONKEY!" banner
INSTA_CARDS = [(100, 100, (18, 20, 23), 12), (960, 250, (18, 20, 23), 12), (1800, 900, (18, 20, 23), 12)]
CARDS_CONTINUE = [(960, 1010, (79, 217, 0), 40)]
TITLE = [(960, 940, (114, 232, 0), 40), (1020, 966, (255, 255, 255), 20),
         (880, 975, (12, 74, 0), 30)]                          # start screen: green START
START_BTN = (960, 966)
HOME = [(930, 945, (144, 227, 0), 40), (990, 900, (47, 222, 0), 40), (80, 1000, (2, 103, 159), 40)]

# Clicks
OK_BTN = (958, 760)
NEXT_BTN = (958, 905)
HOME_BTN = (718, 845)
RESTART_BTN = (958, 805)
RESTART_PAID_BTN = (848, 810)   # never the $ Continue? at (1290, 810)
COLLECT_BTN = (951, 661)
EVENT_BACK_BTN = (78, 58)
CONTINUE_BTN = (958, 1000)
RESTART_CONFIRM_BTN = (1135, 730)
# Menu screens on the way to the map
MAP_SELECT = [(78, 165, (0, 207, 255), 40)]                    # search button
EXPERT_PAGE = [(1181, 757, (64, 159, 255), 40)]                # page dot: Tricky Tracks page
INFERNAL_PAGE = [(1218, 757, (64, 159, 255), 40)]              # page dot: Infernal page
DIFFICULTY = [(530, 600, (156, 120, 66), 30), (860, 600, (156, 120, 66), 30), (78, 55, (255, 255, 255), 30)]   # the reward plaques' frames, not their words
MODE = [(1240, 25, (128, 74, 36), 30), (640, 590, (255, 255, 255), 30), (78, 55, (255, 255, 255), 30)]   # title plate, not its text (any language)
# Home -> Play -> Expert -> next page -> Infernal -> Easy -> Deflation: (click, screen it leads to)
NAV = [((958, 945), MAP_SELECT), ((1335, 975), EXPERT_PAGE), ((1645, 430), INFERNAL_PAGE),
       ((535, 260), DIFFICULTY), ((625, 420), MODE), ((1280, 450), DEFLATION_POPUP)]
UNKNOWN_AFTER = 10   # seconds on an unknown screen before clicking through popups

import keys as _keys
STOP_KEYS = _keys.load("stop")      # settings.json, plus Numpad 0 / Insert / F8
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

# ---------------------------------------------------------------- window
STEAM_URL = "steam://rungameid/960090"   # Bloons TD 6
_hung_since = None


def client_rect():
    h = user32.FindWindowW(None, "BloonsTD6")
    if not h:
        return None
    r = wt.RECT()
    user32.GetClientRect(h, ctypes.byref(r))
    p = wt.POINT(0, 0)
    user32.ClientToScreen(h, ctypes.byref(p))
    return h, p.x, p.y, r.right, r.bottom


def game_process_alive():
    import subprocess
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq BloonsTD6.exe", "/NH"],
                         capture_output=True, text=True).stdout
    return "BloonsTD6.exe" in out


def wait_for_window(seconds):
    """The game's window has no title while it loads: wait for it, don't call it gone."""
    global HWND, OX, OY, W, H
    end = time.time() + seconds
    while time.time() < end:
        rect = client_rect()
        if rect and rect[3] > 0:
            HWND, OX, OY, W, H = rect
            return True
        if not game_process_alive():
            return False
        time.sleep(2)
    return False


def relaunch():
    """Kill whatever is left of the game, start it through Steam, wait for its window."""
    global HWND, OX, OY, W, H
    print("game gone or frozen -> relaunching through Steam")
    os.system("taskkill /f /im BloonsTD6.exe >nul 2>&1")
    for _ in range(60):     # wait until the old window is really gone, or we'd adopt it
        if not client_rect():
            break
        time.sleep(1)
    time.sleep(3)
    os.startfile(STEAM_URL)
    for _ in range(240):
        rect = client_rect()
        if rect and rect[3] > 0:
            break
        time.sleep(1)
    else:
        print("BTD6 did not come back after relaunch")
        os._exit(1)
    time.sleep(20)          # let it load past the splash
    if not wait_for_window(240):   # it swaps windows while loading
        print("BTD6 did not come back after relaunch")
        os._exit(1)
    global _grace_until
    _grace_until = time.time() + 180   # loading: no gone/frozen verdicts for 3 minutes
    # the start screen: press START (bottom middle) until it's gone (user, 2026-11-08)
    pressed = False
    for _ in range(60):                 # up to ~3 minutes of loading
        if in_front():
            im = grab()
            if matches(im, TITLE):
                print("start screen -> START")
                click(*START_BTN)
                pressed = True
            elif pressed or matches(im, HOME):
                break                   # past it: the main loop handles any popups
        time.sleep(3)


_gone_since = None
_grace_until = 0.0

RELOAD_AFTER = 2 * 3600     # s: BTD6 gets slow and heavy the longer it runs (user, 2026-11-08)


def game_age():
    """Seconds BTD6 has been running (its process start time), or None."""
    if not HWND:
        return None
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(HWND, ctypes.byref(pid))
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, pid.value)       # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        ft = [wt.FILETIME() for _ in range(4)]
        if not k32.GetProcessTimes(h, *[ctypes.byref(f) for f in ft]):
            return None
        now = wt.FILETIME()
        k32.GetSystemTimeAsFileTime(ctypes.byref(now))
        t = lambda f: (f.dwHighDateTime << 32 | f.dwLowDateTime) / 1e7
        return t(now) - t(ft[0])
    finally:
        k32.CloseHandle(h)


def reload_if_old():
    """Between games only, on the home screen: after RELOAD_AFTER, restart BTD6 through Steam.
    True if it did. The farm then comes back through the start and home screens as after a crash."""
    if os.environ.get("BTD6_NO_RELOAD"):       # the app's RELOAD OFF
        return False
    age = game_age()
    if age is None or age < RELOAD_AFTER:
        return False
    print(f"BTD6 has run {age / 3600:.1f} h -> reloading it")
    STATS["status"] = "reloading BTD6"
    done = threading.Event()

    def beat():             # relaunch can take minutes: the watchdog must not take it for a stall
        while not done.wait(10):
            STATS["progress"] = time.time()
            save_state(False)
    threading.Thread(target=beat, daemon=True).start()
    try:
        save_state(False)
        relaunch()
    finally:
        done.set()
    return True


def game_ok():
    """False after a crash/freeze, once the game has been relaunched. The game swaps its
    window while loading, so a vanished handle means "look again", not "crashed": only
    no BloonsTD6 window at all for 60 s (or a 60 s freeze) counts."""
    global _hung_since, _gone_since, HWND, OX, OY, W, H
    if time.time() < _grace_until:
        rect = client_rect()
        if rect and rect[3] > 0:
            HWND, OX, OY, W, H = rect
        return True
    if not user32.IsWindow(HWND):
        rect = client_rect()
        if rect and rect[3] > 0:
            HWND, OX, OY, W, H = rect      # same game, new window
            _gone_since = None
            return True
        if game_process_alive():           # still running, window not up (loading)
            if wait_for_window(240):
                _gone_since = None
                return True
        _gone_since = _gone_since or time.time()
        if time.time() - _gone_since > 60:
            _gone_since = None
            relaunch()
            return False
        return True
    _gone_since = None
    # a backgrounded game reads as "not responding": only judge it while it's in front
    if user32.IsHungAppWindow(HWND) and user32.GetForegroundWindow() == HWND:
        _hung_since = _hung_since or time.time()
        if time.time() - _hung_since > 60:
            _hung_since = None
            relaunch()
            return False
    else:
        _hung_since = None
    return True


_rect = client_rect()
if _rect is None:
    HWND = None
    if not (game_process_alive() and wait_for_window(240)):
        relaunch()
else:
    HWND, OX, OY, W, H = _rect


def scr(x, y):
    return OX + round(x * W / 1920), OY + round(y * H / 1080)


# ---------------------------------------------------------------- input
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _U)]


def _send(inp):
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def key(ch, hold=0.03):
    if not in_front():
        return
    vk = ch if isinstance(ch, int) else user32.VkKeyScanW(ord(ch)) & 0xFF if len(ch) == 1 else ch
    sc = user32.MapVirtualKeyW(vk, 0)
    for flags in (0x0008, 0x0008 | 0x0002):  # SCANCODE, then KEYUP
        i = INPUT(type=1)
        i.u.ki = KEYBDINPUT(0, sc, flags, 0, None)
        _send(i)
        time.sleep(hold)
    time.sleep(0.04)


def click(x, y):
    if not in_front():
        return
    move(x, y)
    time.sleep(0.12)                # the game must see the move on a frame before the press
    for flags in (0x0002, 0x0004):  # LEFTDOWN, LEFTUP
        i = INPUT(type=0)
        i.u.mi = MOUSEINPUT(0, 0, 0, flags, 0, None)
        _send(i)
        time.sleep(0.06)
    time.sleep(0.08)


def move(x, y):
    # A real mouse-move event: the game ignores SetCursorPos for the placement ghost.
    # Absolute coordinates are 0..65535 across the primary monitor.
    if not in_front():          # never move the user's mouse while they're in another window
        return
    sx, sy = scr(x, y)
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    i = INPUT(type=0)
    i.u.mi = MOUSEINPUT(round(sx * 65535 / (sw - 1)), round(sy * 65535 / (sh - 1)), 0,
                        0x0001 | 0x8000, 0, None)  # MOVE | ABSOLUTE
    _send(i)


# ---------------------------------------------------------------- screen
_sct = mss.MSS()


def grab():
    g = _sct.grab({"left": OX, "top": OY, "width": W, "height": H})
    return Image.frombytes("RGB", g.size, g.rgb)


def matches(im, checks):
    if not checks:
        return False
    for x, y, rgb, tol in checks:
        px = im.getpixel((round(x * W / 1920), round(y * H / 1080)))
        if any(abs(a - b) > tol for a, b in zip(px, rgb)):
            return False
    return True


def check_stop():
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    if any(user32.GetAsyncKeyState(k) & 0x8000 for k in STOP_KEYS) or (pt.x <= 2 and pt.y <= 2):
        STATS["stopped"] = True
        save_state(False)
        print("stopped by hotkey")
        os._exit(0)
    if _pause_pressed():
        print("paused (Numpad 1 again to resume)")
        status = STATS["status"]
        STATS["status"] = "PAUSED - Numpad 1 to resume"
        while not _pause_pressed():
            pt = wt.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            if any(user32.GetAsyncKeyState(k) & 0x8000 for k in STOP_KEYS):
                STATS["stopped"] = True
                save_state(False)
                print("stopped by hotkey")
                os._exit(0)
            STATS["progress"] = time.time()     # paused on purpose: not "stuck" for the watchdog
            save_state(True)
            time.sleep(0.05)
        STATS["status"] = status
        print("resumed")


PAUSE_KEYS = _keys.load("pause")    # settings.json, plus Numpad 1 / End
_pause_was = {"down": False}


def _pause_pressed():
    """True once per press of Numpad 1 (an edge, so holding it doesn't flicker), or once per
    Pause click in the app (gui.py)."""
    if _pause_was.pop("gui", False):
        return True
    down = any(user32.GetAsyncKeyState(k) & 0x8000 for k in PAUSE_KEYS)
    pressed = down and not _pause_was["down"]
    _pause_was["down"] = down
    return pressed


def wait(seconds):
    end = time.time() + seconds
    while time.time() < end:
        check_stop()
        time.sleep(0.02)


def focus():
    """Bring BTD6 to the front. Windows refuses SetForegroundWindow to background apps unless
    a key was just pressed, so tap Alt first. True if the game is in front afterwards."""
    if user32.GetForegroundWindow() == HWND:
        return True
    if not HWND or not user32.IsWindow(HWND):
        return False                                # game gone: game_ok() deals with it
    user32.ShowWindow(HWND, 9)                      # SW_RESTORE (if minimised)
    fg = user32.GetForegroundWindow()
    fg_tid = user32.GetWindowThreadProcessId(fg, None)
    me = ctypes.windll.kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(me, fg_tid, True)      # borrow the front window's right to switch
    user32.keybd_event(0x12, 0, 0, 0)               # Alt down/up
    user32.keybd_event(0x12, 0, 2, 0)
    user32.BringWindowToTop(HWND)
    user32.SetForegroundWindow(HWND)
    user32.AttachThreadInput(me, fg_tid, False)
    time.sleep(0.3)
    if user32.GetForegroundWindow() != HWND:
        user32.SwitchToThisWindow(HWND, True)
        time.sleep(0.3)
    if user32.GetForegroundWindow() != HWND:
        alt_tab_to_game()
    return user32.GetForegroundWindow() == HWND


def _raw_key(vk, up=False):
    """As scan codes: the Alt+Tab switcher ignores key-code-only Alt releases and stays open."""
    i = INPUT(type=1)
    i.u.ki = KEYBDINPUT(0, user32.MapVirtualKeyW(vk, 0), 0x0008 | (0x0002 if up else 0), 0, None)
    _send(i)


def alt_tab_to_game():
    """Alt+Tab is real input, so Windows always honours it: hold Alt, tap Tab n times
    (n = 1, 2, ...) until the game is the window in front."""
    for n in range(1, 9):
        _raw_key(0x12)                  # Alt down
        for _ in range(n):
            _raw_key(0x09)
            _raw_key(0x09, up=True)
            time.sleep(0.08)
        _raw_key(0x12, up=True)
        time.sleep(0.5)
        if user32.GetForegroundWindow() == HWND:
            return True
        _close_switcher()
    return False


def _close_switcher():
    """If the Alt+Tab switcher stayed open, Esc closes it (it has focus, not the game)."""
    b = ctypes.create_unicode_buffer(64)
    user32.GetWindowTextW(user32.GetForegroundWindow(), b, 64)
    if b.value == "Task Switching":
        _raw_key(0x1B)
        _raw_key(0x1B, up=True)
        time.sleep(0.3)


_held = {"since": None}


AFK_KEYS = _keys.load("afk")    # settings.json, plus Numpad 2: AFK mode on/off
FOCUS_AFTER = 5         # seconds tabbed out before AFK mode pulls the game back


def in_front():
    """Never click or type into another window. Normally it just waits while something else is
    in front; in AFK mode it tabs back into BTD6 after FOCUS_AFTER s."""
    if user32.GetForegroundWindow() == HWND:
        _held["since"] = None
        return True
    if _held["since"] is None:
        _held["since"] = time.time()
        print("BTD6 is not the front window: " + ("tabbing back in" if STATS.get("afk") else "paused until it is"))
    if STATS.get("afk") and time.time() - _held["since"] >= FOCUS_AFTER:
        focus()
        if user32.GetForegroundWindow() == HWND:
            print("tabbed back into BTD6")
            _held["since"] = None
            return True
        _held["since"] = time.time()    # refused: try again in FOCUS_AFTER s
    STATS["progress"] = time.time()     # paused on purpose: don't let the watchdog call it stuck
    STATS["status"] = "paused (game not in front)"
    return False


# ---------------------------------------------------------------- stats
STATS = {"start": time.time(), "wins": 0, "losses": 0, "xp": 0, "mm": 0, "candy": 0,
         "afk": bool(os.environ.get("BTD6_AFK")),     # `watchdog.py <map> afk`, or Numpad 2
         "run_start": None, "last_run": None, "status": "starting"}
_home = {}   # last OCR read of the home screen: level, xp, need, mm


def load_state():
    """Carry the overlay totals across watchdog restarts (state younger than 2 hours)."""
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            st = json.load(f)
        if time.time() - st.get("heartbeat", 0) < 7200 and not st["stats"].get("stopped"):
            STATS.update({k: st["stats"][k] for k in ("start", "wins", "losses", "xp", "mm", "last_run") if k in st["stats"]})
            STATS["candy"] = st["stats"].get("candy", 0)
            # kept across map switches, but a run started with AFK (watchdog ... afk) is always AFK:
            # the old state used to switch an overnight run's AFK back off
            STATS["afk"] = STATS["afk"] or st["stats"].get("afk", False)
            _home.update(st.get("home", {}))
    except Exception:
        pass
    STATS["progress"] = time.time()


def save_state(running):
    st = {"heartbeat": time.time(), "running": running, "stats": STATS, "home": _home}
    try:
        with open(STATE_FILE + ".tmp", "w", encoding="utf-8") as f:
            json.dump(st, f)
        os.replace(STATE_FILE + ".tmp", STATE_FILE)
    except OSError:
        pass


def _ocr(img):
    from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter

    async def run():
        im = img.convert("RGBA")
        w = DataWriter()
        w.write_bytes(im.tobytes())
        bmp = SoftwareBitmap.create_copy_from_buffer(w.detach_buffer(), BitmapPixelFormat.RGBA8,
                                                     im.width, im.height, BitmapAlphaMode.STRAIGHT)
        return (await OcrEngine.try_create_from_user_profile_languages().recognize_async(bmp)).text
    return asyncio.run(run())


def num_text(t):
    """OCR text with every language's thousands separator turned into a comma: 1.234 (German),
    1 234 with a (narrow) no-break space (French), 1'234 (Swiss) all read 1,234."""
    return re.sub(r"[\s\u00a0\u202f']", "", t).replace(".", ",")


def _read(im, box, pattern, prep):
    """OCR a 1920x1080-space box a few ways; first text matching pattern wins."""
    c = im.crop(tuple(round(v * W / 1920) if i % 2 == 0 else round(v * H / 1080)
                      for i, v in enumerate(box)))
    for variant in prep(c):
        m = re.search(pattern, num_text(_ocr(variant)))
        if m:
            return [int(g.replace(",", "")) for g in m.groups()]
    return None


def _gray(c):
    g = ImageOps.expand(c.convert("L"), 30, fill=0)
    return [g, g.resize((g.width * 2, g.height * 2))]


def _green(c):
    """Monkey Money: keep the green digits, drop the leading "$" (OCR reads it as 9 or 5)."""
    c = c.convert("RGB")
    mask = [[(g > 180 and r < 220 and b < 120) for r, g, b in
             (c.getpixel((x, y)) for y in range(c.height))] for x in range(c.width)]
    runs = []                   # column runs of green = glyphs
    for x, col in enumerate(mask):
        if sum(col) >= 2:
            if runs and runs[-1][1] == x - 1:
                runs[-1][1] = x
            else:
                runs.append([x, x])
    runs = [r for r in runs if r[1] - r[0] >= 2]    # specks
    keep = [False] * c.width
    for a, b in runs[1:]:                           # runs[0] is the "$"
        for x in range(a, b + 1):
            keep[x] = True
    o = Image.new("L", c.size, 255)
    o.putdata([0 if mask[x][y] and keep[x] else 255
               for y in range(c.height) for x in range(c.width)])
    return [ImageOps.expand(o.resize((o.width * k, o.height * k), Image.LANCZOS), 40, fill=255)
            for k in (3, 2, 4)]


def read_home(im):
    """Read level, XP and Monkey Money off the home screen and add what changed."""
    try:
        lvl = _read(im, (140, 20, 240, 95), r"(\d+)", _gray)
        xp = _read(im, (230, 30, 520, 85), r"([\d,]+)/([\d,]+)", _gray)
        mm = _read(im, (1690, 35, 1845, 85), r"(\d{1,3}(?:,\d{3})+)", _green)
    except Exception as e:
        print("ocr failed:", e)
        return
    now = {"level": lvl and lvl[0], "xp": xp and xp[0], "need": xp and xp[1], "mm": mm and mm[0]}
    old = _home.copy()
    if old.get("mm") is not None and now["mm"] is not None and 0 <= now["mm"] - old["mm"] < 5000:
        STATS["mm"] += now["mm"] - old["mm"]
    if None not in (old.get("xp"), old.get("level"), old.get("need"), now["xp"], now["level"]):
        if now["level"] == old["level"] and now["xp"] >= old["xp"]:
            STATS["xp"] += now["xp"] - old["xp"]
        elif now["level"] == old["level"] + 1:
            STATS["xp"] += old["need"] - old["xp"] + now["xp"]
    for k, v in now.items():
        if v is not None:
            _home[k] = v
    print("home read:", now)


def _hms(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def overlay():
    """Small always-on-top stats box over the game's top-left. Click-through and left out
    of screen captures, so the farm's own pixel checks never see it."""
    prev = user32.GetForegroundWindow()     # showing the box activates it: give focus back after
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.8)
    root.configure(bg="black")
    pos_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_pos.json")
    try:
        with open(pos_file, encoding="utf-8") as f:
            x, y = json.load(f)
    except Exception:
        x, y = OX + 140, OY + 110
    root.geometry(f"+{x}+{y}")
    label = tk.Label(root, font=("Consolas", 12, "bold"), fg="white", bg="black",
                     justify="left", padx=10, pady=6)
    label.pack()
    root.update()
    hwnd = user32.GetParent(root.winfo_id())
    style = user32.GetWindowLongW(hwnd, -20)                         # GWL_EXSTYLE
    user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20 | 0x80 | 0x08000000)  # LAYERED|TRANSPARENT|TOOLWINDOW|NOACTIVATE
    if prev and user32.GetForegroundWindow() == hwnd:
        user32.SetForegroundWindow(prev)    # Tk took focus anyway: hand it straight back (allowed,
    root.update()                           # since this process holds the foreground right now)
    user32.SetWindowDisplayAffinity(hwnd, 0x11)                      # WDA_EXCLUDEFROMCAPTURE

    # Click-through, except while Ctrl is held: then it can be dragged with the mouse.
    drag = {"grab": None, "on": False}

    def press(e):
        drag["grab"] = (e.x_root - root.winfo_x(), e.y_root - root.winfo_y())

    def move(e):
        if drag["grab"]:
            root.geometry(f"+{e.x_root - drag['grab'][0]}+{e.y_root - drag['grab'][1]}")

    def release(e):
        drag["grab"] = None
        try:
            with open(pos_file, "w", encoding="utf-8") as f:
                json.dump([root.winfo_x(), root.winfo_y()], f)
        except OSError:
            pass

    for w in (root, label):
        w.bind("<ButtonPress-1>", press)
        w.bind("<B1-Motion>", move)
        w.bind("<ButtonRelease-1>", release)

    def watch_ctrl():
        held = bool(user32.GetAsyncKeyState(0x11) & 0x8000)
        if held != drag["on"]:
            drag["on"] = held
            user32.SetWindowLongW(hwnd, -20, (style | 0x80000 | 0x80 | 0x08000000) | (0 if held else 0x20))
            label.config(fg="yellow" if held else "white")
        root.after(50, watch_ctrl)
    watch_ctrl()

    def tick():
        up = time.time() - STATS["start"]
        runs = STATS["wins"] + STATS["losses"]
        hours = max(up / 3600, 1e-9)
        lines = [f"Runs     {runs}  ({STATS['wins']}W {STATS['losses']}L)",
                 f"Uptime   {_hms(up)}"]
        if STATS["last_run"]:
            lines.append(f"Last run {_hms(STATS['last_run'])}")
        lines += [f"XP       +{STATS['xp']:,}  ({STATS['xp'] / hours:,.0f}/h)",
                  f"Cash     +{STATS['mm']:,}  ({STATS['mm'] / hours:,.0f}/h)",
                  f"Candy    +{STATS['candy']:,}  ({STATS['candy'] / hours:,.0f}/h)"]
        if _home.get("level"):
            lines.append(f"Level    {_home['level']}")
        if STATS.get("next"):
            lines.append(f"Next     {STATS['next']}")
        if STATS.get("afk"):
            lines.append("AFK mode")
        lines.append(STATS["status"])
        label.config(text="\n".join(lines))
        root.after(1000, tick)
    tick()
    root.mainloop()


# ---------------------------------------------------------------- farm
def place(hotkey, pos, path):
    move(*pos)
    key(hotkey)
    wait(0.06)
    click(*pos)
    wait(0.12)
    click(*pos)            # select it
    wait(0.08)
    for name, tiers in zip(("top", "mid", "bot"), path):
        for _ in range(tiers):
            key(UPGRADE_KEYS[name])
            wait(0.05)
    click(397, 77)         # the upgrade panel's X (the map can hold removable obstacles)
    wait(0.05)


def find_cards(im):
    """Centres of the insta cards on the dark reveal screen (row y=540)."""
    bg = (18, 20, 23)
    y = round(540 * H / 1080)
    runs = []
    for x in range(W):
        if sum(abs(a - b) for a, b in zip(im.getpixel((x, y)), bg)) > 60:
            if runs and x - runs[-1][1] <= 30:
                runs[-1][1] = x
            else:
                runs.append([x, x])
    return [round((a + b) / 2 * 1920 / W) for a, b in runs if b - a > 80 * W / 1920]


def open_boxes(im):
    """Collection event: click every insta card, Esc back after each, then Continue."""
    if matches(im, CARDS_CONTINUE):
        click(*CONTINUE_BTN)
        wait_for(EVENT, 3)
        return
    for x in find_cards(im):
        click(x, 540)
        if wait_for(INSTA_REVEAL, 2.5):     # Esc as soon as the card shows, not after a fixed wait
            try:
                time.sleep(0.4)             # let the card finish growing in
                read_insta(grab())
            except Exception as e:
                print(f"insta reader: {e}")
        key("\x1b")
        wait_for(INSTA_CARDS, 1.5)


TOWERS = ["Dart Monkey", "Boomerang Monkey", "Bomb Shooter", "Tack Shooter", "Ice Monkey", "Glue Gunner",
          "Desperado", "Sniper Monkey", "Monkey Sub", "Monkey Buccaneer", "Monkey Ace", "Heli Pilot",
          "Mortar Monkey", "Dartling Gunner", "Wizard Monkey", "Super Monkey", "Ninja Monkey", "Alchemist",
          "Druid", "Mermonkey", "Banana Farm", "Spike Factory", "Monkey Village", "Engineer Monkey",
          "Beast Handler"]
GOT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instas_got.json")


def read_insta(im):
    """The insta on the reveal screen ('Ninja Monkey', '0-3-3') -> instas_got.json, for the app's
    list. The picture is kept in featured/got_*.png so a misread can be checked."""
    import difflib
    full = im.convert("RGB").resize((1920, 1080))
    flat = re.sub(r"\s+", " ", _ocr(full))
    m = re.search(r"([0-5])\s*[-–—]\s*([0-5])\s*[-–—]\s*([0-5])", flat)
    tiers = "-".join(m.groups()) if m else None
    # the name: white title letters under the picture (the game's font reads 'ALcuemrsT' whole-screen),
    # so OCR that line alone as black on white, then take the closest tower name
    line = full.crop((560, 770, 1360, 835)).convert("L").point(lambda v: 0 if v > 200 else 255)
    name = re.sub(r"[^a-z]", "", _ocr(line.resize((line.width * 2, line.height * 2))).lower())
    keys = {t.lower().replace(" ", ""): t for t in TOWERS}
    keys.update({t.lower().replace(" monkey", "").replace(" ", ""): t for t in TOWERS})
    hit = difflib.get_close_matches(name, keys, n=1, cutoff=0.6) if name else []
    tower = keys[hit[0]] if hit else None
    flat = f"{flat} | name line: {name}"
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "featured")
    os.makedirs(folder, exist_ok=True)
    im.save(os.path.join(folder, time.strftime("got_%Y%m%d_%H%M%S.png")))
    print(f"insta: {tiers or '?'} {tower or '?'}" + ("" if tower and tiers else f"  (read: {flat[:80]})"))
    try:
        with open(GOT_FILE, encoding="utf-8") as f:
            got = json.load(f)
    except (OSError, ValueError):
        got = []
    got.append({"at": time.strftime("%Y-%m-%d %H:%M"), "tower": tower or "?", "tiers": tiers or "?"})
    tmp = GOT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(got, f)
    os.replace(tmp, GOT_FILE)


FEATURED = [(1435, 410), (1560, 410), (1435, 520), (1560, 520)]   # the 4 featured instas


FEATURED_BOX = (1355, 320, 1640, 640)      # the 4 tiles, as saved to featured/
INSTA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instas")   # one picture per monkey


def featured_box(im):
    """The featured tiles, scaled to 1920x1080 pixels (285x320)."""
    (x0, y0), (x1, y1) = scr(*FEATURED_BOX[:2]), scr(*FEATURED_BOX[2:])
    return im.convert("RGB").crop((x0 - OX, y0 - OY, x1 - OX, y1 - OY)).resize((285, 320))


def which_insta(box, i):
    """The instas/ picture tile i shows ('02'), or None. Matched with a small shift search: the
    tiles pulse and the panel can slide in. A best match well ahead of the next one is required."""
    from PIL import ImageChops, ImageStat
    if not hasattr(which_insta, "refs"):
        # each picture at a few sizes too: the tiles grow and shrink (hover, the box's pulse)
        which_insta.refs = {}
        for f in sorted(os.listdir(INSTA_DIR)):
            if f.endswith(".png"):
                im = Image.open(os.path.join(INSTA_DIR, f)).convert("RGB")
                sizes = []
                for s in (0.84, 0.92, 1.0, 1.08):
                    n = round(64 * s)
                    r = im.resize((n, n), Image.BILINEAR).crop((n // 2 - 22, n // 2 - 22, n // 2 + 22, n // 2 + 22))
                    sizes.append(r)
                    # the insta picked last box is drawn faded: 41% pale blue over it (measured 2026-11-09)
                    sizes.append(Image.blend(r, Image.new("RGB", r.size, (190, 243, 255)), 0.41))
                which_insta.refs[f[:-4]] = sizes
    cx, cy = (80, 205, 80, 205)[i], (90, 90, 200, 200)[i]
    px = list(box.crop((cx - 32, cy - 32, cx + 32, cy + 32)).getdata())
    # tile blue ~ (10, 90, 140), faded ~ (85, 150, 190); the purple backdrop has less green than red
    if sum(b > r + 40 and g > r + 20 for r, g, b in px) < 0.08 * len(px):
        return None         # no blue tile there (the panel isn't up): the purple backdrop matched Spikes
    tiles = [box.crop((cx - 22 + dx, cy - 22 + dy, cx + 22 + dx, cy + 22 + dy))
             for dy in range(-8, 9, 2) for dx in range(-8, 9, 2)]
    # faded (picked last box) only if the tile's own background is pale: a faded Bomb matched dim Mortars
    corners = [box.getpixel((cx + sx, cy + sy)) for sx in (-27, 27) for sy in (-27, 27)]
    pale = sum(r > 50 and b > 150 for r, g, b in corners) >= 3
    ds = []
    for name, sizes in which_insta.refs.items():
        d = min(sum(ImageStat.Stat(ImageChops.difference(t, r)).mean) / 3 for t in tiles for r in sizes[pale::2])
        ds.append((d, name))
    ds.sort()
    # measured on 468 saved tiles: right answers came in under 50 and under 0.9 of the runner-up
    return ds[0][1] if ds[0][0] < 50 and ds[0][0] < 0.9 * ds[1][0] else None


def insta_picks():
    """The user's featured instas, in order (the app's INSTAS picker, gui.json). Empty: pick none."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui.json"), encoding="utf-8") as f:
            return [str(p) for p in json.load(f).get("instas", [])]
    except (OSError, ValueError):
        return []


def pick_featured(im):
    """On a full candy box, click the first of the user's picked instas that's featured (each
    user picks their own in the app). Every featured row is saved to featured/."""
    picks = insta_picks()
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "featured")
    os.makedirs(folder, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    # the panel slides in and its tiles pulse: wait until two looks agree
    from PIL import ImageChops, ImageStat
    box = featured_box(im)
    for _ in range(6):
        time.sleep(0.3)
        nxt = featured_box(grab())
        moved = sum(ImageStat.Stat(ImageChops.difference(box, nxt)).mean) / 3
        box = nxt
        if moved < 6:
            break
    box.save(os.path.join(folder, f"{stamp}.png"))
    if not picks:
        return False
    seen = [which_insta(box, i) for i in range(4)]
    print("featured instas: " + ", ".join(s or "?" for s in seen))
    for p in picks:
        if p in seen:
            x, y = FEATURED[seen.index(p)]
            print(f"featured insta {p}: picking it")
            click(x, y)
            wait(1.5)
            grab().save(os.path.join(folder, f"{stamp}_picked.png"))
            return True
    return False


# --- the game's Auto Start setting: the farm presses Space for round 1 only, so with Auto Start
# off the game sat after the first round (user, 2026-11-07). In the Esc pause menu, by picture.
PAUSE = [(1296, 800, (98, 202, 0), 40), (846, 800, (0, 192, 222), 40), (620, 800, (1, 192, 222), 40),
         (1070, 800, (0, 192, 221), 40)]                     # Continue (green), Store/Home/Restart (blue)
AUTO_START_ON = [(1290, 306, (120, 238, 0), 40), (1356, 306, (0, 213, 255), 40)]    # green track, knob right
AUTO_START_OFF = [(1290, 306, (0, 213, 255), 40), (1356, 306, (52, 30, 14), 40)]    # knob left, dark track
AUTO_START_BTN = (1323, 306)
CONTINUE_BTN = (1296, 830)
AUTO_START_OK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_start.ok")   # the watchdog clears it on start
AUTO_START = {"checked": os.path.exists(AUTO_START_OK)}


def ensure_auto_start():
    """Once per launch of the farm, in a game: Esc -> pause menu -> Auto Start on -> Continue."""
    if AUTO_START["checked"] or os.environ.get("BTD6_NO_AUTOSTART") or not in_front() or not matches(grab(), IN_GAME):
        return      # (BTD6_NO_AUTOSTART: the app's AUTO START OFF)
    for _ in range(2):              # the first Esc may only close a tower's panel
        key(0x1B)
        if wait_for(PAUSE, 2):
            break
        if not matches(grab(), IN_GAME):
            return print("auto start: the pause menu didn't come up")
    else:
        return print("auto start: the pause menu didn't come up")
    wait_for(AUTO_START_ON, 2) or wait_for(AUTO_START_OFF, 0.5)    # the menu grows in: let it settle
    time.sleep(0.2)
    im = grab()
    if matches(im, AUTO_START_OFF):
        click(*AUTO_START_BTN)
        time.sleep(0.6)
        ok = matches(grab(), AUTO_START_ON)
        print("auto start was OFF: turned it on" if ok else "auto start was OFF and didn't turn on")
        AUTO_START["checked"] = ok
    elif matches(im, AUTO_START_ON):
        print("auto start is on")
        AUTO_START["checked"] = True
    else:
        print("auto start: switch not found in the pause menu")
        AUTO_START["checked"] = True        # don't open the menu every game over it
    if AUTO_START["checked"]:
        open(AUTO_START_OK, "w").close()    # later games of this launch skip the check
    click(*CONTINUE_BTN)
    if not wait_for(IN_GAME, 3):
        click(*CONTINUE_BTN)


def wait_for(checks, timeout):
    """Poll until the screen matches; False on timeout."""
    end = time.time() + timeout
    while time.time() < end:
        check_stop()
        if matches(grab(), checks):
            return True
        time.sleep(0.05)
    return False


def on_mode_screen():
    """Called on the difficulty-mode screen before picking a mode. infernal_impop.py checks the hero here."""


# The hero the game has selected, as last picked by a farm (hero.txt). A map whose HERO is already
# selected skips the hero screen, about 15 s (user, 2026-11-08). A hero picked by hand in the game
# isn't seen: the map plays with it until a map with another hero picks again.
HERO = None             # a map with a hero sets its name: F.HERO = "Etienne"
HERO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hero.txt")


def hero_now():
    try:
        return open(HERO_FILE, encoding="utf-8").read().strip() or None
    except OSError:
        return None


def mode_screen():
    if HERO and hero_now() == HERO:
        print(f"{HERO} is already the hero")
        return
    on_mode_screen()


# Expert maps (read 2026-11-03). The Expert button opens whichever Expert page was last
# used, so pages are found by the lit page dot, never assumed.
EXPERT_DOTS = {1: 1181, 2: 1218, 3: 1255}      # page dot x at y=757
EXPERT_MAPS = {   # name: (page, tile centre)
    "Tricky Tracks": (1, (535, 270)), "Glacial Trail": (1, (960, 270)), "Dark Dungeons": (1, (1385, 270)),
    "Sanctuary": (1, (535, 580)), "Ravine": (1, (960, 580)), "Flooded Valley": (1, (1385, 580)),
    "Infernal": (2, (535, 270)), "Bloody Puddles": (2, (960, 270)), "Workshop": (2, (1385, 270)),
    "Quad": (2, (535, 580)), "Dark Castle": (2, (960, 580)), "Muddy Puddles": (2, (1385, 580)),
    "#Ouch": (3, (535, 270)),
}


def expert_page():
    im = grab()
    for page, x in EXPERT_DOTS.items():
        if matches(im, [(x, 757, (64, 159, 255), 40)]):
            return page
    return None


MAP_NAME = "map"     # the farm's map, for the stats box (nav_to sets it)


def press(x, y):
    """A slow, careful click for the home-screen buttons, which ignore a quick one now and then:
    slide onto the button from just off it, then hold the press longer."""
    move(x - 58, y - 45)
    time.sleep(0.15)
    move(x, y)
    time.sleep(0.1)
    if not in_front():
        return
    user32.SetCursorPos(*scr(x, y))     # what clicks these buttons reliably by hand (clk.py)
    time.sleep(0.15)
    for flags in (0x0002, 0x0004):  # LEFTDOWN, LEFTUP
        i = INPUT(type=0)
        i.u.mi = MOUSEINPUT(0, 0, 0, flags, 0, None)
        _send(i)
        time.sleep(0.15)


def expert_open(map_name):
    """Home -> Play -> Expert -> the map's page. Back to the map's tile, or None."""
    page, tile = EXPERT_MAPS[map_name]
    im = grab()
    if matches(im, HOME):
        pics.note_home(im)
    for _ in range(5):                  # Play sometimes ignores a click: wiggle onto it, press longer, retry
        if not in_front():
            return None
        press(958, 945)
        if wait_for(MAP_SELECT, 2.5):
            break
        print("nav: Play didn't open the maps, clicking again")
    else:
        return print("nav: map select did not come up")
    time.sleep(0.5)
    click(1335, 975)                    # Expert
    time.sleep(1.2)
    for _ in range(4):
        now = expert_page()
        if now == page:
            break
        click(*((1645, 430) if now is None or now < page else (272, 430)))
        time.sleep(1.2)
    else:
        return print(f"nav: could not reach Expert page {page}")
    return tile


# --- maps or heroes this player doesn't have: skip them ------------------------------------------
# A downloaded farm can meet a map or hero the player hasn't unlocked. The farm notes it in
# skipped_maps.json and exits with code 5: in bonus mode the watchdog plays a map the player has
# for a game and checks the bonus again; with one map picked it stops and says why. A skip is
# forgotten after SKIP_FOR seconds, in case it was unlocked meanwhile.
SKIP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skipped_maps.json")
SKIP_FOR = 6 * 3600
NAV_FAILS = {}          # map -> clicks on its tile in a row that didn't open it


def skipped():
    """{map: why} for maps skipped in the last SKIP_FOR seconds."""
    try:
        d = json.load(open(SKIP_FILE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {m: v["why"] for m, v in d.items() if time.time() - v.get("t", 0) < SKIP_FOR}


def skip_map(map_name, why):
    """Note the map as unplayable and exit (code 5) so the watchdog moves on."""
    try:
        d = json.load(open(SKIP_FILE, encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    d[map_name] = {"why": why, "t": time.time()}
    with open(SKIP_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
    print(f"skipping {map_name}: {why}")
    save_state(False)
    sys.stdout.flush()
    os._exit(5)


HERO_SELECT_BTN = (1110, 615)
HERO_BTN_BOX = (960, 575, 1260, 660)     # around the green Select under the picked hero


def hero_select(name):
    """In the hero list with the hero's tile clicked: press Select, unless the button there is
    an Unlock (a locked hero: never press it, it buys with Monkey Money) -> skip this map."""
    wait(0.5)
    c = grab().crop(tuple(round(v * W / 1920) if i % 2 == 0 else round(v * H / 1080)
                          for i, v in enumerate(HERO_BTN_BOX)))
    t = ""
    for v in (c, c.resize((c.width * 2, c.height * 2)), ImageOps.invert(c.convert("L"))):
        t += " " + _ocr(v).upper()
    # anything like SELECT(ED) = fine; a price or "Unlock" / "Level" with no SELECT = locked
    looks_select = any(k in t for k in ("SELECT", "ELECT", "SELEC"))
    if not looks_select and ("UNLOCK" in t or "LEVEL" in t or re.search(r"\d{3}", t)):
        print(f"hero {name} is locked (button reads {t.strip()!r})")
        for _ in range(4):      # hero list -> mode -> difficulty -> map list -> Home / event screen
            click(78, 55)
            wait(1.5)
        skip_map(MAP_NAME, f"hero {name} not unlocked")
    click(*HERO_SELECT_BTN)
    try:
        with open(HERO_FILE, "w", encoding="utf-8") as f:
            f.write(name)
    except OSError:
        pass


# --- prices (Impoppable), shared by every farm: prices.json -----------------------------------
# {"Ice Monkey": {"place": 480, "top": [tier 1, tier 2, ...], "mid": [...], "bot": [...]}, ...}
PRICES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prices.json")
_PRICES = {}


def _prices():
    if not _PRICES:
        try:
            _PRICES.update(json.load(open(PRICES_FILE, encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return _PRICES


# An Impoppable build played on Easy / Medium / Hard Standard (`watchdog.py <map>_impop.py@easy`):
# the same towers and rounds, Standard mode, prices scaled from the Impoppable ones.
DIFF = (os.environ.get("BTD6_DIFF") or "").lower() or None
DIFF_BTN = {"easy": (625, 420), "medium": (958, 420), "hard": (1290, 420)}
STANDARD_BTN = (640, 560)


def price(tower, path=None, tier=None):
    """price("Ice Monkey") to place it; price("Ice Monkey", "bot", 3) for Cryo Cannon.
    None if it isn't in prices.json. Off Impoppable (DIFF), scaled like the game does."""
    t = _prices().get(tower) or {}
    if path is None:
        v = t.get("place")
    else:
        row = t.get(path) or []
        v = row[tier - 1] if 0 < tier <= len(row) and row[tier - 1] else None
    if v and DIFF in DIFF_BTN:
        v = int(5 * round(v / 1.2 * DIFFICULTY_MULT[DIFF] / 5))
    return v


COSTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tower_costs.json")
_COSTS = {}
DIFFICULTY_MULT = {"easy": 0.85, "medium": 1.0, "hard": 1.08, "impoppable": 1.2}


def cost(tower, path=None, tier=None, difficulty="medium"):
    """Any monkey's cost on any difficulty, from tower_costs.json (Medium prices read off the
    Monkeys screen by price_scan.py), scaled like the game: x0.85 / 1 / 1.08 / 1.2, to the
    nearest $5. cost("Ice Monkey", "mid", 5, "impoppable") = Absolute Zero. None if unknown."""
    if not _COSTS:
        try:
            _COSTS.update(json.load(open(COSTS_FILE, encoding="utf-8")))
        except (OSError, ValueError):
            return None
    t = _COSTS.get(tower) or {}
    base = t.get("place") if path is None else (t.get(path) or [None] * 5)[tier - 1]
    if not base:
        return None
    return int(5 * round(base * DIFFICULTY_MULT[difficulty.lower()] / 5))


def set_price(tower, path, tier, v):
    """Save a price (path None = placing it) to prices.json."""
    if DIFF in DIFF_BTN:                # prices.json holds Impoppable prices only
        return
    t = _prices().setdefault(tower, {})
    if path is None:
        t["place"] = int(v)
    else:
        row = t.setdefault(path, [])
        row.extend([None] * (tier - len(row)))
        row[tier - 1] = int(v)
    try:
        with open(PRICES_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(_PRICES, f, indent=1)
    except OSError:
        pass


BONUS = bool(os.environ.get("BTD6_BONUS"))      # set by `watchdog.py bonus`
BONUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bonus_map.txt")
EVENT_BTN = (1840, 325)         # the pumpkin on the home screen (moved down a slot when the
                                # Odyssey button came in, 2026-11-05: found by colour now)


def event_btn(im=None):
    """Where the pumpkin is in the home screen's right icon column: the 70 px stretch with the
    most pumpkin orange (the icons above it shift as events come and go)."""
    im = im or grab()
    rows = []
    for y in range(100, 600, 10):
        n = 0
        for x in range(1800, 1880, 2):
            r, g, b = im.getpixel((round(x * W / 1920), round(y * H / 1080)))[:3]
            n += r > 220 and 90 < g < 170 and b < 70
        rows.append((y, n))
    best = max(range(len(rows) - 6), key=lambda i: sum(n for _, n in rows[i:i + 7]))
    if sum(n for _, n in rows[best:best + 7]) < 40:
        return EVENT_BTN
    return (1840, rows[best + 3][0])
EVENT_PLAY_BTN = (1810, 960)
BONUS_TILE = (535, 655)         # 4th tile of the event's map list: always an Expert map
BONUS_TITLE = (380, 505, 700, 550)


def _norm(name):
    return re.sub(r"[^A-Z]", "", name.upper())


def bonus_name(im):
    """The 4th tile's title. The OCR is flaky on this font, so read it several ways: an exact
    hit on any read wins, else the closest name to any read (difflib, 0.75 or better)."""
    import difflib
    got = mapsig.which(im, BONUS_TILE, EXPERT_MAPS)    # by its picture: any game language
    if got:
        return got
    reads = []
    for box in (BONUS_TITLE, (420, 500, 660, 550)):
        c = im.crop(tuple(round(v * W / 1920) if i % 2 == 0 else round(v * H / 1080)
                          for i, v in enumerate(box)))
        for v in _gray(c) + [c, c.resize((c.width * 2, c.height * 2)), ImageOps.invert(c.convert("L"))]:
            got = _norm(_ocr(v))
            if not got:
                continue
            for name in EXPERT_MAPS:
                if _norm(name) in got:
                    return name
            reads.append(got)
    best, score = None, 0.75
    for got in reads:
        for name in EXPERT_MAPS:
            r = difflib.SequenceMatcher(None, _norm(name), got).ratio()
            if r >= score:
                best, score = name, r
    return best


def bonus_open(map_name):
    """Home -> pumpkin -> Play. If the bonus Expert map is this farm's map, True (its tile is
    clicked next); if it's another map, note it and exit so the watchdog starts that farm."""
    im = grab()
    if matches(im, HOME):
        pics.note_home(im)
    # the farm that switched here left the event's map list open: carry on from it
    name = None if matches(im, HOME) else bonus_name(im)
    if name is None:
        for _ in range(4):
            press(*event_btn())
            if wait_for(EVENT, 3):
                break
        else:
            print("bonus: event screen did not come up")
            return False
        press(*EVENT_PLAY_BTN)
        for _ in range(6):
            wait(1)
            name = bonus_name(grab())
            if name:
                break
    if name is None:
        print("bonus: could not read the bonus map, going the normal way")
        click(78, 55)
        wait(2)
        click(*EVENT_BACK_BTN)
        wait(2)
        return "expert"
    if name in skipped():
        print(f"bonus map is {name}, which this player can't play ({skipped()[name]}): another map meanwhile")
        with open(BONUS_FILE, "w", encoding="utf-8") as f:
            f.write(name)
        click(78, 55)
        wait(2)
        click(*EVENT_BACK_BTN)
        wait(2)
        save_state(False)
        sys.stdout.flush()
        os._exit(5)
    if name == map_name:
        print(f"bonus map: {name}")
        return True
    print(f"bonus map is {name}, not {map_name}: switching farms")
    with open(BONUS_FILE, "w", encoding="utf-8") as f:
        f.write(name)
    # stay on the map list: the next farm picks it up from here (backing out home and coming
    # back cost ~15 s, and the bonus map changes after every win)
    save_state(False)
    sys.stdout.flush()
    os._exit(4)


# Collection Event candies per win (user's numbers): Deflation 3, Easy Standard 13, Impoppable 54
CANDY = {(1280, 450): 3, (1280, 740): 54}
MODE_BTN = {"btn": None}        # the mode the farm picks, set by nav_to


def candy_per_win():
    btn = MODE_BTN["btn"]
    if btn is None:             # rejoined a game without navigating: peek at the farm's nav
        consts = getattr(getattr(nav, "__code__", None), "co_consts", ())
        btn = next((c for c in consts if c in CANDY), None)
    return CANDY.get(btn, 13)


def nav_to(map_name, difficulty_btn, mode_btn, final=None):
    """Home -> Play -> Expert -> the map's page (stepped by the dots) -> map -> difficulty -> mode."""
    global MAP_NAME
    if DIFF in DIFF_BTN and tuple(mode_btn) == (1280, 740):   # an Impoppable build on Standard
        difficulty_btn, mode_btn, final = DIFF_BTN[DIFF], STANDARD_BTN, IN_GAME
    if not in_front():                  # tabbed out: wait, don't run the menus blind
        wait(1)
        return
    MAP_NAME = map_name
    MODE_BTN["btn"] = tuple(mode_btn)
    STATS["status"] = f"loading {map_name}"
    if BONUS:                           # the Collection Event's bonus map instead of the Expert list
        STATS["status"] = "checking the event"      # this farm's map may not be the event's
        save_state(False)
        got = bonus_open(map_name)
        if not got:
            return
        STATS["status"] = f"loading {map_name}"
        tile = BONUS_TILE if got is True else expert_open(map_name)
        if tile is None:
            return
    else:
        tile = expert_open(map_name)
        if tile is None:
            return
    final = final or DEFLATION_POPUP        # Standard mode goes straight into the game: IN_GAME
    for pos, screen in ((tile, DIFFICULTY), (difficulty_btn, MODE), (mode_btn, final)):
        for _ in range(2):
            click(*pos)
            if screen is final and wait_for(RESTART_CONFIRM, 2):
                click(*RESTART_CONFIRM_BTN)     # "Overwrite save?" (a game was left unfinished): OK
            if wait_for(screen, 20 if screen is final else 6):
                break
        else:
            if pos == tile:             # the map's own tile didn't open it: locked map?
                NAV_FAILS[map_name] = NAV_FAILS.get(map_name, 0) + 1
                if NAV_FAILS[map_name] >= 3:
                    click(78, 55)
                    skip_map(map_name, "map not unlocked (its tile never opened it)")
            return print("nav: screen did not come up, retrying from wherever we are")
        if pos == tile:
            NAV_FAILS.pop(map_name, None)
        time.sleep(0.3)
        if screen is MODE:
            mode_screen()
    NAV_DONE["t"] = time.time()     # a game opened from the menu is new, whatever round it reads
    if final is DEFLATION_POPUP:
        click(*OK_BTN)
    for _ in range(3):              # a second popup can follow ("Monkey Teams" on that day's map)
        if not wait_for(DEFLATION_POPUP, 1.5):
            break
        click(*OK_BTN)
    if wait_for(IN_GAME, 5):
        ensure_auto_start()


NAV_DONE = {"t": 0}


def nav():
    # Infernal, Easy, Deflation through nav_to (finds the Expert page, the bonus route, and skips
    # the map if it's locked). The old fixed clicks below are kept unused.
    return nav_to("Infernal", (625, 420), (1280, 450))


def _old_nav():
    for pos, screen in NAV:
        click(*pos)
        if not wait_for(screen, 20 if screen is DEFLATION_POPUP else 6):
            print("nav: screen did not come up, retrying from wherever we are")
            return
        time.sleep(0.3)     # page slides finish after the dot moves
        if screen is MODE:
            mode_screen()
    if final is DEFLATION_POPUP:
        click(*OK_BTN)          # dismiss the Deflation instructions straight away


def setup():
    print("placing towers")
    key(" ")               # start the round first: the bloons take a few seconds to arrive
    wait(0.1)
    key(" ")               # double speed
    place(SNIPER_KEY, SNIPER_POS, SNIPER_PATH)
    place(WIZARD_KEY, WIZARD_POS, WIZARD_PATH)
    place(ALCH_KEY, ALCH_POS, ALCH_PATH)
    print("running")


def on_defeat(im):
    """Called on every defeat screen. infernal_impop.py logs the loss here."""


def go_home():
    """Leave whatever game is open (used when the watchdog switches farms)."""
    for _ in range(20):
        check_stop()
        im = grab()
        if matches(im, HOME):
            return
        if matches(im, DEFEAT_PAID):
            click(628, 810)
        elif matches(im, DEFEAT) or matches(im, VICTORY_MENU):
            click(*HOME_BTN) if matches(im, VICTORY_MENU) else click(738, 810)
        elif matches(im, IN_GAME):
            key("")
            wait(1)
            click(846, 855)            # pause menu: Home
        elif matches(im, TITLE):
            click(*START_BTN)
        else:
            click(960, 200)     # never a blind Esc: on the start screen it quits
        wait(3)


def ingame():
    """Called every poll while in a game. Deflation needs nothing; infernal_impop.py overrides it."""


def clear_popup(n):
    """Level-ups, rewards, anything else: click the title-banner area. Never the middle or
    bottom (a defeat screen keeps its paid "Continue?" there) and never Esc (on the start
    screen Esc quits the game)."""
    if n >= 2 and n % 2 == 0 and matches(grab(), BACK_ARROW):
        # a menu the farm doesn't know (the hero screen, left open when a nav failed while tabbed
        # out: 17 min of clicking at the top, 2026-11-09): its back arrow, top left
        print("unknown screen with a back arrow -> back")
        click(78, 55)
        return
    print("unknown screen, clicking through")
    click(960, 200)


BACK_ARROW = [(110, 30, (0, 221, 255), 30), (78, 88, (0, 193, 255), 30), (60, 55, (255, 255, 255), 20)]   # the menus' top-left back button


def farm():
    running = "--running" in sys.argv   # started mid-game with the towers already down
    if running:
        STATS["run_start"] = time.time()
    load_state()
    time.sleep(1)                       # let the overlay come up (the game is never pulled forward:
                                        # the farm waits until the user puts BTD6 in front)
    if "--go-home" in sys.argv:
        go_home()
    games = 0
    unknown_since = None
    tries = 0
    while True:
        check_stop()
        save_state(running)
        if not game_ok():
            STATS["status"] = "relaunched after crash"
            running = False
        im = grab()
        known = True
        if matches(im, DEFLATION_POPUP):
            click(*OK_BTN)
            wait(0.3)
            running = False
            STATS["status"] = "placing towers"
        elif matches(im, VICTORY_STATS):
            if not STATS.get("won_this_game"):      # the screen lingers (and Next can be
                STATS["won_this_game"] = True       # ignored while tabbed out): count it once
                games += 1
                print(f"win #{games}")
                STATS["wins"] += 1
                STATS["candy"] += candy_per_win()
                if STATS["run_start"]:
                    STATS["last_run"] = time.time() - STATS["run_start"]
                if os.environ.get("BTD6_ONE_GAME"):
                    save_state(False)
                    sys.stdout.flush()
                    os._exit(6)         # a stand-in map's game is done: check the bonus map again
            STATS["progress"] = time.time()
            STATS["status"] = "won, heading home"
            click(*NEXT_BTN)
            wait(0.8)
        elif matches(im, RESTART_CONFIRM):
            click(*RESTART_CONFIRM_BTN)
            NAV_DONE["t"] = time.time()     # a restarted game is new too
            wait(1)
            running = False
        elif matches(im, DEFEAT_PAID):
            if not STATS.get("lost_this_game"):      # the screen lingers: count it once
                print("defeat -> restart (not the paid continue)")
                on_defeat(im)
                STATS["losses"] += 1
                STATS["lost_this_game"] = True
            STATS["progress"] = time.time()
            STATS["status"] = "lost, restarting"
            click(*RESTART_PAID_BTN)
            wait(0.6)
        elif matches(im, DEFEAT):
            if not STATS.get("lost_this_game"):      # the screen lingers: count it once
                print("defeat -> restart")
                on_defeat(im)
                STATS["losses"] += 1
                STATS["lost_this_game"] = True
            STATS["progress"] = time.time()
            STATS["status"] = "lost, restarting"
            click(*RESTART_BTN)
            wait(0.6)
        elif matches(im, VICTORY_MENU):
            click(*HOME_BTN)
            wait(1)
        elif matches(im, MODE) or matches(im, DIFFICULTY):
            # Whatever map this screen belongs to is unknown (it was a different map's screen
            # once, and the farm played Glacial Trail): back out to the home screen and nav from there.
            print("mode/difficulty screen -> back to home, map unknown")
            click(78, 55)
            wait(2)
        elif matches(im, TITLE):
            print("start screen -> START")
            click(*START_BTN)
            wait(4)
        elif matches(im, INSTA_REVEAL):
            key("\x1b")
            wait_for(INSTA_CARDS, 1.5)
        elif matches(im, INSTA_CARDS):
            print("opening candy box")
            STATS["status"] = "opening candy box"
            open_boxes(im)
        elif matches(im, EVENT):
            px = im.getpixel((round(COLLECT_BTN[0] * W / 1920), round(COLLECT_BTN[1] * H / 1080)))
            if px[1] > 180 and px[0] < 150 and px[2] < 100:     # green Collect button
                pick_featured(im)
                print("collecting candy box")
                click(*COLLECT_BTN)
                wait_for(INSTA_CARDS, 3)
            else:
                click(*EVENT_BACK_BTN)
                wait(4)
        elif matches(im, HOME):
            # BTD6's 2-hourly reload goes here, off the home screen: closing the game on the victory
            # screen left the won game saved at round 41 ("Continue saved game?", Flooded Valley
            # and Workshop, 2026-11-09)
            if reload_if_old():
                running = False
                continue
            print("home -> back into the map")
            STATS["status"] = "reading stats"
            read_home(im)
            STATS["status"] = f"loading {MAP_NAME}"
            nav()
        elif matches(im, DEFLATION_POPUP):
            # a popup with one green OK over the game (Deflation rules, "Monkey Teams" on that
            # day's map): it blocked every placement on Flooded Valley, 2026-11-05
            print("popup over the game: OK")
            click(*OK_BTN)
            wait(1)
        elif matches(im, IN_GAME):
            if not running:
                STATS["status"] = "placing towers"
                STATS["lost_this_game"] = False
                STATS["won_this_game"] = False
                setup()
                running = True
                STATS["run_start"] = time.time()
                STATS["progress"] = time.time()
            if user32.GetForegroundWindow() == HWND:
                STATS["status"] = "tabbed in"
            else:
                STATS["status"] = "tabbed out"
                STATS["progress"] = time.time()     # waiting on purpose: keep the watchdog quiet
            ingame()
        else:
            known = False
        if known:
            unknown_since, tries = None, 0
        elif BONUS and unknown_since is None and bonus_name(im):
            print("on the bonus map list")      # left open by the farm that switched here
            nav()
        elif unknown_since is None:
            unknown_since = time.time()
        elif time.time() - unknown_since > UNKNOWN_AFTER and BONUS and bonus_name(im):
            print("on the bonus map list")      # left open by the farm that switched here
            nav()
            unknown_since, tries = None, 0
        elif time.time() - unknown_since > UNKNOWN_AFTER:
            clear_popup(tries)
            tries += 1
            unknown_since = time.time() - UNKNOWN_AFTER + 3
        wait(0.25)


def farm_guarded():
    import traceback
    try:
        farm()
    except SystemExit:
        raise
    except BaseException:
        traceback.print_exc()
        print("farm crashed: exiting so the watchdog restarts it")
        sys.stdout.flush()
        os._exit(3)


GUI_CMD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui_cmd.txt")


def gui_command():
    """"pause", "stop" or "afk" from the app, or None. Read once, then deleted; a word older
    than 15 s is dropped, so a stale Stop can't end the next run."""
    try:
        age = time.time() - os.path.getmtime(GUI_CMD)
        with open(GUI_CMD, encoding="utf-8") as f:
            word = f.read().strip().lower()
        os.remove(GUI_CMD)
    except OSError:
        return None
    return word if age < 15 else None


def hotkeys():
    """Stop keys in their own thread, polled fast with the 'pressed since last poll' bit,
    so a quick tap is never missed, even if the farm thread is busy or dead."""
    afk_was = False
    next_cmd = 0
    while True:
        gui = None
        if time.time() >= next_cmd:         # the app's buttons (gui.py) drop a word in this file
            next_cmd = time.time() + 0.25
            gui = gui_command()
        if gui == "pause":
            _pause_was["gui"] = True
        afk_down = any(user32.GetAsyncKeyState(k) & 0x8000 for k in AFK_KEYS)
        if gui == "afk" or (afk_down and not afk_was):
            STATS["afk"] = not STATS.get("afk")
            print("AFK mode " + ("on: tabs back into BTD6 by itself" if STATS["afk"] else "off"))
            sys.stdout.flush()
        afk_was = afk_down
        if gui == "stop" or any(user32.GetAsyncKeyState(k) & 0x8001 for k in STOP_KEYS):
            STATS["stopped"] = True
            save_state(False)
            print("stopped by hotkey")
            sys.stdout.flush()
            os._exit(0)
        time.sleep(0.05)


def main():
    threading.Thread(target=hotkeys, daemon=True).start()
    threading.Thread(target=farm_guarded, daemon=True).start()
    overlay()


if __name__ == "__main__":
    main()
