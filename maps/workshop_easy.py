# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Workshop, Easy, Standard (40 rounds), hero Sauda. Runs on dark_castle_impop.py's
machinery (checked placing/upgrading, in-order queue, loop guards, overlay Next line).
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import time

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I
import dark_castle_impop as D

# Placement points read off the user's game 2026-11-03 (towers draw ~20-30 px above their point).
# All four placed in Sandbox 2026-11-03.
GLUE = (215, 622)
SAUDA = (1495, 629)     # 617 was refused in Sandbox
BOMB = (1005, 405)
BOOM = (1000, 492)

D.FUZZ["LAST"] = ("LAS", "AST")
I.TOKENS.update(y=("GLUE", "GUNN"), u=("SAUDA", "AUDA", "JIANG"), e=("BOMB", "SHOOT", "BOM", "OOTE", "GOM"))

D.PRE = I.P("y", GLUE) + I.T(GLUE, "LAST") + I.P("u", SAUDA)     # free Glue on Last, then Sauda
I.STEPS = {0: (I.U(GLUE, top=2, mid=1) + I.U(GLUE, mid=1) + I.U(GLUE, top=1)   # 2-1-0, 2-2-0, 3-2-0
              + I.P("w", BOOM, (0, 3, 2))
              + I.P("e", BOMB, (2, 4, 0)))}
D.MAULER_SPOTS = []
# The Glue Gunner's right-side panel title reads badly; it stands alone, so any panel its
# click opens is its own (tiers still come off the pips).
I.NAME.pop(repr(GLUE), None)
D.DONE_AFTER = 0
D.NICE = {repr(GLUE): "Glue", repr(SAUDA): "Sauda", repr(BOOM): "Boomerang", repr(BOMB): "Bomb"}
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

# Bomb ability (MOAB Assassin, key 2) half a second into round 40. Reading the counter takes
# two reads, which was too late (the MOAB leaked first), so it fires off the start-round press
# that follows round 39; seeing round 40 any other way fires it at once.
FIRED = set()
_start_round, _run_queue, _setup = I.start_round, D.run_queue, D.setup


def fire():
    if "r40" in FIRED:
        return
    FIRED.add("r40")
    F.wait(0.5)
    I.drop_ghost()
    F.key("2")
    print("round 40: bomb ability")


def start_round():
    _start_round()
    if I.G["round"] >= 39:
        fire()


def run_queue():
    # from round 39 on, read the counter on every poll (one read, not two) so 40 is caught at once
    if "r40" not in FIRED and I.G["round"] >= 39:
        if I.G["round"] >= 40 or I.read_round(F.grab()) == 40:
            fire()
    _run_queue()


def setup():
    FIRED.clear()
    HERO_TRIES["n"] = 0
    _setup()


HERO_TRIES = {"n": 0}
_try_op = I.try_op


def try_op(op):
    """Sauda places once. If her place keeps failing (the farm was restarted with her already
    down and her panel didn't confirm it), count her as standing after 6 tries so she can't
    hold up the whole build."""
    done = _try_op(op)
    if op[0] == "place" and op[2][0] == "u" and not done:
        HERO_TRIES["n"] += 1
        if HERO_TRIES["n"] >= 6:
            print("assuming Sauda is already standing")
            done = True
    return done


I.try_op = try_op
I.start_round, I.run_queue = start_round, run_queue
F.setup = setup

SAUDA_TILE = (405, 798)         # hero list: row 4, column 3
STANDARD_BTN = (640, 560)


def pick_sauda():
    F.click(105, 975)           # Change Hero
    F.wait(2)
    F.click(*SAUDA_TILE)
    F.wait(1)
    F.click(*I.SELECT_BTN)
    F.wait(1)
    F.click(78, 55)             # back to the mode screen
    F.wait(2)


F.on_mode_screen = pick_sauda
F.nav = lambda: F.nav_to("Workshop", (625, 420), STANDARD_BTN, final=F.IN_GAME)   # Easy, Standard

if __name__ == "__main__":
    F.main()
