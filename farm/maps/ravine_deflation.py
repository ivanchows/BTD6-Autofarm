# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Ravine, Easy, Deflation, hero Obyn.
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import time

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I

# the user's own placing clicks in Sandbox, 2026-11-04 (Druid 3 moved left so it fits)
VILLAGE = I.Spot("Village", (786, 302))
BUCC = I.Spot("Buccaneer", (701, 440))
OBYN = I.Spot("Obyn", (824, 184))
DRUID1 = I.Spot("Druid 1", (867, 250))
DRUID2 = I.Spot("Druid 2", (726, 135))
DRUID3 = I.Spot("Druid 3", (700, 205))
BOOMER = I.Spot("Boomerang", (745, 816))
I.TOKENS.update(k=("VILL",), c=("BUCC", "CCAN"), g=("DRUID",), w=("BOOM", "RANG"))

START = "start"     # hit play and double speed here
BUILD = [("k", VILLAGE, (0, 2, 1)), ("c", BUCC, (4, 2, 0)), START, ("u", OBYN, None),
         ("g", DRUID1, (0, 3, 0)), ("g", DRUID2, (0, 3, 0)), ("g", DRUID3, (0, 3, 0)),
         ("w", BOOMER, (3, 0, 2))]
I.FINAL.clear()
for _b in BUILD:
    if _b != START and _b[2]:
        I.FINAL[repr(_b[1])] = list(_b[2])


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
    for b in BUILD:
        if b == START:
            I.deselect()
            I.start_round()
            continue
        key, spot, path = b
        F.STATS["next"] = spot.name + (f" {'-'.join(map(str, path))}" if path else "")
        if key == "u":
            I.NAME.pop(repr(spot), None)       # Obyn's skin title can't be read
        else:
            I.NAME[repr(spot)] = I.TOKENS[key]
        if place(key, spot) and path:
            upgrade(spot, path)
    I.deselect()
    F.STATS["next"] = "done"    # nothing left to do until the game ends: no clicks, no mouse moves
    print("running, cash", I.read_cash())
    F.STATS["status"] = "running"


OBYN_TILE = (103, 414)          # hero list: row 2, column 1


def pick_obyn():
    F.click(105, 975)           # Change Hero
    F.wait(2)
    F.click(*OBYN_TILE)
    F.wait(1)
    F.hero_select("Obyn")     # (skips the map if Obyn is locked)
    F.wait(1)
    F.click(78, 55)             # back to the mode screen
    F.wait(2)


F.setup = setup
F.ingame = lambda: None
F.on_mode_screen = pick_obyn
F.HERO = "Obyn"
F.nav = lambda: F.nav_to("Ravine", (625, 420), (1280, 450))       # Easy, Deflation

if __name__ == "__main__":
    F.main()
