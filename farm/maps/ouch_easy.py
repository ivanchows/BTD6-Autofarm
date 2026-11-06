# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: #Ouch, Easy, Standard (40 rounds), no hero. Runs on dark_castle_impop.py's machinery
(checked placing/upgrading, in-order queue, loop guards, overlay Next line).
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I
import dark_castle_impop as D

# Subs: the user's own placing clicks in Sandbox 2026-11-04 (970,625 was refused: off the pool)
DART = (125, 630)
DESP = (368, 205)
SUB_TL = (726, 479)         # top-left of the pond
SUB_BR = (966, 612)         # bottom-right of the pond
SUB_TR = (966, 492)         # top-right of the pond (round 27)

I.TOKENS.update(q=("DART",), x=("SUB",), **{";": ("DESP", "PERAD")})

D.PRE = I.P("q", DART) + I.P("x", SUB_BR) + I.P("x", SUB_TL)       # free Dart and 2 Subs
I.STEPS = {
    0: (I.P(";", DESP, (0, 1, 0))
        + I.U(SUB_BR, top=2, bot=3)                                # bottom-right 2-0-3
        + I.U(SUB_TL, top=2, mid=2) + I.T(SUB_TL, "STRONG")),       # top-left 2-2-0, Strong
    27: (I.U(SUB_BR, bot=1)                                        # bottom-right 2-0-4
         + I.P("x", SUB_TR, (2, 0, 4))),                           # top-right 2-0-4
}
D.MAULER_SPOTS = []
D.DONE_AFTER = 27
D.NICE = {repr(DART): "Dart", repr(DESP): "Desperado", repr(SUB_TL): "top-left Sub",
          repr(SUB_BR): "bottom-right Sub", repr(SUB_TR): "top-right Sub"}
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

STANDARD_BTN = (640, 560)

F.on_mode_screen = lambda: None    # no hero: whatever is selected just isn't placed
F.nav = lambda: F.nav_to("#Ouch", (625, 420), STANDARD_BTN, final=F.IN_GAME)   # Easy, Standard

if __name__ == "__main__":
    F.main()
