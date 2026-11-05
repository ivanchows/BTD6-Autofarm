"""The farm's own Pause and Stop keys, read from keys.json (so a keyboard without a numpad can pick others)."""
import ctypes
import json
import os

NAMES = {"NUMPAD" + str(i): 0x60 + i for i in range(10)}
NAMES.update({"F" + str(i): 0x6F + i for i in range(1, 25)})
NAMES.update(END=0x23, HOME=0x24, INSERT=0x2D, DELETE=0x2E, PAGEUP=0x21, PAGEDOWN=0x22,
             PAUSE=0x13, SCROLLLOCK=0x91, UP=0x26, DOWN=0x28, LEFT=0x25, RIGHT=0x27)
EXTRA = {"pause": (0x61, 0x23), "stop": (0x60, 0x2D, 0x77)}   # Numpad 1 / End, Numpad 0 / Insert / F8 always work


def vk(name):
    n = name.strip().upper().replace(" ", "")
    if n in NAMES:
        return NAMES[n]
    if len(n) == 1:
        return ctypes.windll.user32.VkKeyScanW(ord(name.strip())) & 0xFF
    print(f"keys.json: unknown key {name!r}")
    return None


def load(which):
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys.json"), encoding="utf-8") as f:
            got = json.load(f).get(which, [])
    except (OSError, ValueError):
        got = []
    got = [got] if isinstance(got, str) else got
    return tuple(dict.fromkeys([k for k in map(vk, got) if k] + list(EXTRA[which])))
