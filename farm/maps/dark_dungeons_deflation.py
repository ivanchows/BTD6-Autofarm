# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Dark Dungeons, Easy, Deflation. One 0-2-5 Dart Monkey (user, 2026-11-08), no hero.
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import time

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I

DART = I.Spot("Dart", (862, 451), (862, 476))   # the user's spot (2026-11-08); a little lower if refused
I.TOKENS.update(q=("DART",))
I.FINAL.clear()
I.FINAL[repr(DART)] = [0, 2, 5]


def place(key, spot):
    for _ in range(15):
        F.check_stop()
        result = I.try_place(key, spot)
        print("place", spot.name, spot.xy, result)
        if result == "placed":
            return True
        if result == "blocked":
            spot.i = (spot.i + 1) % len(spot.cands)
        F.wait(0.3)
    print("!! could not place", spot.name)
    return False


def upgrade(spot, path):
    I.TARGET[repr(spot)] = [0, 0, 0]
    ops = I.U(spot, *path)
    end = time.time() + 40
    while ops and time.time() < end:
        F.check_stop()
        if I.try_op(ops[0]):
            print(ops.pop(0)[3])
        else:
            F.wait(0.1)
    if ops:
        print("!! not bought:", "; ".join(op[3] for op in ops))
    I.deselect()


def setup():
    print("placing towers")
    F.STATS["status"] = "placing towers"
    I.SEL["pos"] = None
    DART.i = 0
    F.STATS["next"] = "Dart 0-2-5"
    I.NAME[repr(DART)] = I.TOKENS["q"]
    if place("q", DART):
        upgrade(DART, (0, 2, 5))
    I.start_round()
    F.STATS["next"] = "done"    # nothing left to do until the game ends: no clicks, no mouse moves
    print("running, cash", I.read_cash())
    F.STATS["status"] = "running"


F.setup = setup
F.nav = lambda: F.nav_to("Dark Dungeons", (625, 420), (1280, 450))   # Easy, Deflation
F.ingame = lambda: None
F.on_mode_screen = lambda: None

if __name__ == "__main__":
    F.main()
