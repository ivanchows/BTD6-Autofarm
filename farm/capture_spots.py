"""Point at a tower, press Numpad 1 (or End with NumLock off) to save that spot.
Names come from the command line: uv run capture_spots.py STRIKER DART ..."""
import ctypes
import ctypes.wintypes as wt
import sys
import time

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
NAMES = sys.argv[1:] or ["SNIPER_TOP", "SNIPER_BOT", "VILLAGE", "ALCH"]

was = False
i = 0
print("point at", NAMES[i], "and press Numpad 1", flush=True)
while i < len(NAMES):
    down = bool(user32.GetAsyncKeyState(0x61) & 0x8000 or user32.GetAsyncKeyState(0x23) & 0x8000)   # Numpad 1 / End
    if down and not was:
        p = wt.POINT()
        user32.GetCursorPos(ctypes.byref(p))
        print(f"{NAMES[i]} = ({p.x}, {p.y})", flush=True)
        i += 1
        if i < len(NAMES):
            print("point at", NAMES[i], "and press Numpad 1", flush=True)
    was = down
    time.sleep(0.02)
