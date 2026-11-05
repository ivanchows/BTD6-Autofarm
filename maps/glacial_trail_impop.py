# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Glacial Trail, Hard, Impoppable, hero Silas. Runs on dark_castle_impop.py's
machinery: checked placing/upgrading, in-order queue, loop guards. Spots in glacial_spots.json
(the cluster ones are the user's own placing clicks, Sandbox 2026-11-03).
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import json
import os

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I
import dark_castle_impop as D

SP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "glacial_spots.json"),
                    encoding="utf-8"))
T = tuple
DART, NINJA, SILAS = T(SP["dart"]), T(SP["ninja"]), T(SP["silas"])
ICE1, ICE2, ICE3 = T(SP["ice1_top"]), T(SP["ice2_bottom"]), T(SP["ice3_top"])
SPIKE, MORTAR, MORTAR_AIM = T(SP["spike"]), T(SP["mortar"]), T(SP["mortar_target"])
ICE2_CLICK = (1355, 705)        # its placement point opens Silas's panel; this opens its own

D.FUZZ["SMART"] = ("SMAR", "MART")
I.TOKENS.update(d=("NINJ", "INJA"), t=("ICE",), n=("MORT", "RTAR"), u=("SILAS", "ILAS"),
                j=("SPIKE", "FACT"), q=("DART",))

# Steps are queued one round before the round they're listed for, so the cash goes straight in.
D.PRE = I.P("q", DART) + I.P("d", NINJA) + I.T(NINJA, "STRONG")
STEPS = {
    0: (I.U(NINJA, top=2)                                         # Ninja 2-0-0
        + I.P("u", SILAS)
        + I.P("t", ICE1)
        + I.P("j", SPIKE, (0, 0, 2)) + I.T(SPIKE, "SMART") + I.U(SPIKE, bot=1)    # 0-0-3, Smart
        + I.P("n", MORTAR, (0, 2, 0)) + [("mortar", None, (MORTAR,), "mortar -> aim under ice 1")]
        + I.U(SPIKE, top=2) + I.U(SPIKE, bot=1)                  # 2-0-3, then 2-0-4
        + I.U(ICE1, top=2, bot=3) + I.T(ICE1, "STRONG") + I.U(ICE1, bot=1)),       # 2-0-3, 2-0-4
    46: (I.P("t", ICE2, (0, 3, 0)) + I.P("t", ICE3, (0, 0, 3)) + I.T(ICE3, "STRONG")
         + I.U(ICE2, top=2, mid=1) + I.U(ICE3, top=2, bot=1)),   # 2-4-0 and 2-0-4
    68: I.U(SPIKE, bot=1),                                       # Perma-Spike 2-0-5
    79: I.U(ICE1, bot=1),                                        # Icicle Impale 2-0-5
    85: I.U(ICE3, bot=1),                                        # second Icicle Impale
    92: I.U(ICE2, mid=1),                                        # Absolute Zero 2-5-0
    96: I.U(MORTAR, top=2, mid=2),                               # Mortar 2-4-0
}
I.STEPS = {max(0, k - 1) if k else 0: v for k, v in STEPS.items()}
I.DURING = {}
D.RETRY = 0.25
D.MAX_TRIES["mortar"] = 4
D.MAULER_SPOTS = []
D.DONE_AFTER = 95
D.NICE = {repr(DART): "Dart", repr(NINJA): "Ninja", repr(SILAS): "Silas", repr(ICE1): "Ice 1",
          repr(ICE2): "Ice 2 (bottom)", repr(ICE3): "Ice 3 (top)", repr(SPIKE): "Spike Factory",
          repr(MORTAR): "Mortar"}
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

_select, _try_op = I.select, I.try_op


def select(pos):
    return _select(ICE2_CLICK if I.xy(pos) == ICE2 else pos)


def try_op(op):
    """'mortar': open its panel, press Set Target, click the aim point under Ice 1."""
    if op[0] != "mortar":
        return _try_op(op)
    I.select(MORTAR)
    F.wait(0.3)
    dx = I.panel_side(F.grab())
    if dx is None or not I.selected_is(MORTAR):
        I.deselect()
        return False
    F.click(220 + dx, 375)
    F.wait(0.4)
    F.click(*MORTAR_AIM)
    F.wait(0.3)
    I.deselect()
    return True


I.select, I.try_op = select, try_op

SILAS_TILE = (103, 798)         # hero list: row 4, column 1


def pick_silas():
    F.click(105, 975)           # Change Hero
    F.wait(2)
    F.click(*SILAS_TILE)
    F.wait(1)
    F.click(*I.SELECT_BTN)
    F.wait(1)
    F.click(78, 55)             # back to the mode screen
    F.wait(2)


F.on_mode_screen = pick_silas
F.nav = lambda: F.nav_to("Glacial Trail", (1290, 420), (1280, 740))     # Hard, Impoppable

if __name__ == "__main__":
    F.main()
