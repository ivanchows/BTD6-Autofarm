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
                 (960, 150, (255, 235, 0), 40)]                # stats card + Next
VICTORY_MENU = [(1200, 820, (113, 232, 0), 40), (560, 460, (102, 153, 217), 40)]  # Home/Review/Freeplay
DEFEAT = [(990, 840, (240, 185, 0), 40), (960, 340, (255, 59, 0), 40), (570, 500, (93, 145, 214), 40)]
DEFEAT_PAID = [(880, 840, (250, 193, 0), 40), (960, 340, (255, 59, 0), 40)]  # 4 buttons, last = paid Continue
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
DIFFICULTY = [(625, 566, (154, 228, 44), 40), (78, 55, (255, 255, 255), 30)]
MODE = [(960, 45, (0, 0, 0), 30), (640, 590, (255, 255, 255), 30), (78, 55, (255, 255, 255), 30)]
# Home -> Play -> Expert -> next page -> Infernal -> Easy -> Deflation: (click, screen it leads to)
NAV = [((958, 945), MAP_SELECT), ((1335, 975), EXPERT_PAGE), ((1645, 430), INFERNAL_PAGE),
       ((535, 260), DIFFICULTY), ((625, 420), MODE), ((1280, 450), DEFLATION_POPUP)]
UNKNOWN_AFTER = 10   # seconds on an unknown screen before clicking through popups

STOP_KEYS = (0x60, 0x2D, 0x77)  # Numpad 0, Numpad 0 with NumLock off (Insert), F8
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


_gone_since = None
_grace_until = 0.0


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
    vk = user32.VkKeyScanW(ord(ch)) & 0xFF if len(ch) == 1 else ch
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


PAUSE_KEYS = (0x61, 0x23)   # Numpad 1, and End (Numpad 1 with NumLock off)
_pause_was = {"down": False}


def _pause_pressed():
    """True once per press of Numpad 1 (an edge, so holding it doesn't flicker)."""
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


def in_front():
    """Never click or type into another window. The farm doesn't pull the game forward any
    more (user's call): while something else is in front it just waits, and carries on
    once BTD6 is the front window again."""
    if user32.GetForegroundWindow() == HWND:
        _held["since"] = None
        return True
    if _held["since"] is None:
        _held["since"] = time.time()
        print("BTD6 is not the front window: paused until it is")
    STATS["progress"] = time.time()     # paused on purpose: don't let the watchdog call it stuck
    STATS["status"] = "paused (game not in front)"
    return False


# ---------------------------------------------------------------- stats
STATS = {"start": time.time(), "wins": 0, "losses": 0, "xp": 0, "mm": 0,
         "run_start": None, "last_run": None, "status": "starting"}
_home = {}   # last OCR read of the home screen: level, xp, need, mm


def load_state():
    """Carry the overlay totals across watchdog restarts (state younger than 2 hours)."""
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            st = json.load(f)
        if time.time() - st.get("heartbeat", 0) < 7200 and not st["stats"].get("stopped"):
            STATS.update({k: st["stats"][k] for k in ("start", "wins", "losses", "xp", "mm", "last_run")})
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


def _read(im, box, pattern, prep):
    """OCR a 1920x1080-space box a few ways; first text matching pattern wins."""
    c = im.crop(tuple(round(v * W / 1920) if i % 2 == 0 else round(v * H / 1080)
                      for i, v in enumerate(box)))
    for variant in prep(c):
        m = re.search(pattern, _ocr(variant).replace(" ", "").replace(".", ","))
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
    user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20 | 0x80)  # LAYERED|TRANSPARENT|TOOLWINDOW
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
            user32.SetWindowLongW(hwnd, -20, (style | 0x80000 | 0x80) | (0 if held else 0x20))
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
                  f"Cash     +{STATS['mm']:,}  ({STATS['mm'] / hours:,.0f}/h)"]
        if _home.get("level"):
            lines.append(f"Level    {_home['level']}")
        if STATS.get("next"):
            lines.append(f"Next     {STATS['next']}")
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
    click(1000, 1060)      # deselect on the lava (unplaceable, harmless)
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
        wait(2.5)
        return
    for x in find_cards(im):
        click(x, 540)
        wait(2.5)
        key("\x1b")
        wait(1.5)


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
    """Called on the difficulty-mode screen before picking a mode. impoppable.py checks the hero here."""


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


def nav_to(map_name, difficulty_btn, mode_btn):
    """Home -> Play -> Expert -> the map's page (stepped by the dots) -> map -> difficulty -> mode."""
    page, tile = EXPERT_MAPS[map_name]
    click(958, 945)
    if not wait_for(MAP_SELECT, 6):
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
    for pos, screen in ((tile, DIFFICULTY), (difficulty_btn, MODE), (mode_btn, DEFLATION_POPUP)):
        for _ in range(2):
            click(*pos)
            if screen is DEFLATION_POPUP and wait_for(RESTART_CONFIRM, 2):
                click(*RESTART_CONFIRM_BTN)     # "Overwrite save?" (a game was left unfinished): OK
            if wait_for(screen, 20 if screen is DEFLATION_POPUP else 6):
                break
        else:
            return print("nav: screen did not come up, retrying from wherever we are")
        time.sleep(0.3)
        if screen is MODE:
            on_mode_screen()
    click(*OK_BTN)


def nav():
    for pos, screen in NAV:
        click(*pos)
        if not wait_for(screen, 20 if screen is DEFLATION_POPUP else 6):
            print("nav: screen did not come up, retrying from wherever we are")
            return
        time.sleep(0.3)     # page slides finish after the dot moves
        if screen is MODE:
            on_mode_screen()
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
    """Called on every defeat screen. impoppable.py logs the loss here."""


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
    """Called every poll while in a game. Deflation needs nothing; impoppable.py overrides it."""


def clear_popup(n):
    """Level-ups, rewards, anything else: click the title-banner area. Never the middle or
    bottom (a defeat screen keeps its paid "Continue?" there) and never Esc (on the start
    screen Esc quits the game)."""
    print("unknown screen, clicking through")
    click(960, 200)


def farm():
    running = "--running" in sys.argv   # started mid-game with the towers already down
    if running:
        STATS["run_start"] = time.time()
    load_state()
    time.sleep(1)                       # let the overlay come up, then give the game focus
    focus()
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
            focus()
        im = grab()
        known = True
        if matches(im, DEFLATION_POPUP):
            click(*OK_BTN)
            wait(0.3)
            running = False
            STATS["status"] = "placing towers"
        elif matches(im, VICTORY_STATS):
            games += 1
            print(f"win #{games}")
            STATS["wins"] += 1
            STATS["progress"] = time.time()
            if STATS["run_start"]:
                STATS["last_run"] = time.time() - STATS["run_start"]
            STATS["status"] = "won, heading home"
            click(*NEXT_BTN)
            wait(0.8)
        elif matches(im, RESTART_CONFIRM):
            click(*RESTART_CONFIRM_BTN)
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
        elif matches(im, MODE):
            print("mode screen -> picking the mode")   # left here by a restart
            on_mode_screen()
            click(*NAV[-1][0])
            wait_for(DEFLATION_POPUP, 20)
        elif matches(im, DIFFICULTY):
            print("difficulty screen -> picking it")   # nav got cut short
            i = [screen is DIFFICULTY for _, screen in NAV].index(True)
            click(*NAV[i + 1][0])
            wait_for(MODE, 6)
        elif matches(im, TITLE):
            print("start screen -> START")
            click(*START_BTN)
            wait(4)
        elif matches(im, INSTA_REVEAL):
            key("\x1b")
            wait(1.5)
        elif matches(im, INSTA_CARDS):
            print("opening candy box")
            STATS["status"] = "opening candy box"
            open_boxes(im)
        elif matches(im, EVENT):
            px = im.getpixel((round(COLLECT_BTN[0] * W / 1920), round(COLLECT_BTN[1] * H / 1080)))
            if px[1] > 180 and px[0] < 150 and px[2] < 100:     # green Collect button
                print("collecting candy box")
                click(*COLLECT_BTN)
                wait(3)
            else:
                click(*EVENT_BACK_BTN)
                wait(4)
        elif matches(im, HOME):
            print("home -> back into the map")
            STATS["status"] = "reading stats"
            read_home(im)
            STATS["status"] = "loading Infernal"
            nav()
        elif matches(im, IN_GAME):
            if not running:
                STATS["status"] = "placing towers"
                STATS["lost_this_game"] = False
                setup()
                running = True
                STATS["run_start"] = time.time()
                STATS["progress"] = time.time()
            STATS["status"] = "farming"
            ingame()
        else:
            known = False
        if known:
            unknown_since, tries = None, 0
        elif unknown_since is None:
            unknown_since = time.time()
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


def hotkeys():
    """Stop keys in their own thread, polled fast with the 'pressed since last poll' bit,
    so a quick tap is never missed, even if the farm thread is busy or dead."""
    while True:
        if any(user32.GetAsyncKeyState(k) & 0x8001 for k in STOP_KEYS):
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
