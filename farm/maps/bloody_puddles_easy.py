# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Bloody Puddles, Easy, Standard (40 rounds), no hero. Runs on dark_castle_impop.py's
machinery (checked placing/upgrading, in-order queue, loop guards, overlay Next line).
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I
import dark_castle_impop as D

# Placement points, all seven placed in Sandbox 2026-11-04 to match the user's layout
SUB_TOP = (1190, 175)       # top-right puddle
SUB_BOT = (500, 675)        # middle-left puddle
DART_BOT = (1295, 895)
DART_TOP = (355, 255)
SNIPER = (700, 55)          # top edge
ALCH_TOP = (1195, 280)      # by the top Sub
ALCH_BOT = (350, 685)       # by the bottom Sub

I.TOKENS.update(x=("SUB",), q=("DART",), z=("MPER", "NIPE", "SNIP", "IPER"), f=("ALC", "HEM"))

D.PRE = I.P("x", SUB_TOP) + I.P("x", SUB_BOT)                     # both Subs before round 1
I.STEPS = {0: (I.U(SUB_TOP, top=1, bot=1)                         # top Sub 1-0-1
               + I.U(SUB_BOT, top=1, bot=1)                       # bottom Sub 1-0-1
               + I.U(SUB_TOP, top=1)                              # top Sub 2-0-1
               + I.P("q", DART_BOT, (0, 0, 2))
               + I.U(SUB_BOT, top=1)                              # bottom Sub 2-0-1
               + I.P("q", DART_TOP, (0, 0, 2))
               + I.P("z", SNIPER, (1, 0, 2))
               + I.U(SUB_BOT, bot=1) + I.U(SUB_TOP, bot=1)        # 2-0-2 each
               + I.U(SUB_BOT, bot=1) + I.U(SUB_TOP, bot=1)        # 2-0-3 each
               + I.U(SUB_BOT, bot=1) + I.U(SUB_TOP, bot=1)        # 2-0-4 each
               + I.P("f", ALCH_TOP, (3, 0, 0))
               + I.P("f", ALCH_BOT, (2, 0, 0)))}
D.MAULER_SPOTS = []
D.DONE_AFTER = 0
D.NICE = {repr(SUB_TOP): "top Sub", repr(SUB_BOT): "bottom Sub", repr(DART_BOT): "bottom Dart",
          repr(DART_TOP): "top Dart", repr(SNIPER): "Sniper", repr(ALCH_TOP): "Alchemist",
          repr(ALCH_BOT): "Alchemist 2"}
# The Sniper's panel title has read as nothing to the OCR on other maps; it stands alone
I.NAME.pop(repr(SNIPER), None)
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

STANDARD_BTN = (640, 560)

F.on_mode_screen = lambda: None    # no hero: whatever is selected just isn't placed
F.nav = lambda: F.nav_to("Bloody Puddles", (625, 420), STANDARD_BTN, final=F.IN_GAME)   # Easy, Standard

if __name__ == "__main__":
    F.main()
