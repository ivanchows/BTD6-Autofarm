# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Quad, Easy, Standard (40 rounds), hero Etienne. Runs on dark_castle_impop.py's machinery
(checked placing/upgrading, in-order queue, loop guards, overlay Next line) with its own build.
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I
import dark_castle_impop as D

# Placement points, all four tested in Sandbox 2026-11-03
ETIENNE = (1265, 560)
DART = (780, 825)
BUCC = (840, 470)       # in the pond (840, 430 is on its rim: refused, tested in Sandbox)
DRUID = (450, 575)      # left of the pond, beside the path

I.TOKENS.update(u=("ETN", "ETIEN", "TIENNE"), c=("BUCC", "CCAN", "CANEER"),
                g=("DRUID", "RUID"))

D.PRE = I.P("u", ETIENNE) + I.P("q", DART) + I.P("c", BUCC)       # before round 1
I.STEPS = {0: (I.U(BUCC, mid=2) + I.U(BUCC, top=2) + I.U(BUCC, top=1)     # 0-2-0, 2-2-0, 3-2-0
              + I.P("g", DRUID, (1, 3, 0)))}                                # then a 1-3-0 Druid
D.MAULER_SPOTS = []
D.DONE_AFTER = 0
D.NICE = {repr(ETIENNE): "Etienne", repr(DART): "Dart", repr(BUCC): "Buccaneer", repr(DRUID): "Druid"}
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

ETIENNE_TILE = (254, 798)       # hero list: row 4, column 2
STANDARD_BTN = (640, 560)       # mode screen, top-left button


def pick_etienne():
    F.click(105, 975)           # Change Hero
    F.wait(2)
    F.click(*ETIENNE_TILE)
    F.wait(1)
    F.click(*I.SELECT_BTN)
    F.wait(1)
    F.click(78, 55)             # back to the mode screen
    F.wait(2)


F.on_mode_screen = pick_etienne
F.nav = lambda: F.nav_to("Quad", (625, 420), STANDARD_BTN, final=F.IN_GAME)   # Easy, Standard
F.NAV = [((958, 945), F.MAP_SELECT), ((1335, 975), F.EXPERT_PAGE), ((1645, 430), F.INFERNAL_PAGE),
         ((535, 580), F.DIFFICULTY), ((625, 420), F.MODE), (STANDARD_BTN, F.IN_GAME)]

if __name__ == "__main__":
    F.main()
