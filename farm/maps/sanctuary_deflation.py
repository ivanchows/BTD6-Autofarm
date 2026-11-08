# /// script
# dependencies = ["mss", "pillow", "numpy", "opencv-python-headless",
#                 "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Sanctuary, Easy, Deflation, hero Obyn. Everything goes on the temple before
the first round (the temple's live shift comes from sanctuary_impop.py), then it plays itself.
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import time

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import sanctuary_impop as S      # temple tracking, Fixed spots, Obyn pick
import core as F
import infernal_impop as I

# the user's Sandbox placements, 2026-11-04 (temple at home)
VILLAGE = S.Fixed("Village", (847, 175), "temple")      # the user's own placing clicks
BUCC = S.Fixed("Buccaneer", (736, 179), "temple")       # in the temple's left pool
OBYN = S.Fixed("Obyn", (835, 291), "temple")
WIZARD = S.Fixed("Wizard", (915, 266), "temple")
DRUID = S.Fixed("Druid", (753, 266), "temple")
I.TOKENS.update(k=("VILL",), c=("BUCC", "CCAN"), a=("WIZ", "ZARD"), g=("DRUID",))

BUILD = [("k", VILLAGE, (0, 2, 1)), ("c", BUCC, (4, 2, 0)), ("u", OBYN, None),
         ("a", WIZARD, (2, 0, 4)), ("g", DRUID, (1, 1, 0))]
I.FINAL.clear()                 # sanctuary_impop's limits (its Wizard is 5-0-2) would block 2-0-4
for _k, _s, _p in BUILD:
    if _p:
        I.FINAL[repr(_s)] = list(_p)


def place(key, spot):
    for _ in range(15):
        F.check_stop()
        result = I.try_place(key, spot)
        print("place", spot.name, spot.xy, result)
        if result == "placed":
            return True
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
    S.SELNAME["n"] = None
    for key, spot, path in BUILD:
        F.STATS["next"] = spot.name + (f" {'-'.join(map(str, path))}" if path else "")
        if key in ("k", "c", "a", "g"):
            I.NAME[repr(spot)] = I.TOKENS[key]
        else:
            I.NAME.pop(repr(spot), None)       # Obyn's skin title can't be read
        if place(key, spot) and path:
            upgrade(spot, path)
    I.deselect()
    I.start_round()
    F.STATS["next"] = "done"    # nothing left to do until the game ends: no clicks, no mouse moves
    print("running, cash", I.read_cash())
    F.STATS["status"] = "running"


F.setup = setup
F.ingame = lambda: None
F.nav = lambda: F.nav_to("Sanctuary", (625, 420), (1280, 450))       # Easy, Deflation

if __name__ == "__main__":
    F.main()
