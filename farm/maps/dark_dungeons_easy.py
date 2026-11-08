# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Dark Dungeons, Easy, Standard (40 rounds), hero Obyn. Runs on dark_castle_impop.py's
machinery (checked placing/upgrading, in-order queue, loop guards, overlay Next line).
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I
import dark_castle_impop as D

# Placement points, all six placed in Sandbox 2026-11-04 (Obyn's is the user's own click)
OBYN = (575, 895)
DART = (925, 950)
SUB = (1445, 885)       # in the pool
SNIPER = (180, 165)
BOMB = (790, 960)
HELI = (950, 545)       # its pad

I.TOKENS.update(u=("OBYN", "GREEN", "MOUNT", "GUARD"), q=("DART",), x=("SUB",),
                z=("MPER", "NIPE", "SNIP", "IPER"), e=("BOMB", "SHOOT", "BOM", "OOTE", "GOM"),
                b=("HELI", "PILOT"))

D.PRE = I.P("u", OBYN) + I.P("q", DART) + I.P("x", SUB)            # before round 1
I.STEPS = {0: (I.U(SUB, bot=1)                                      # Sub 0-0-1
               + I.P("z", SNIPER, (1, 0, 0))
               + I.U(SUB, mid=2, bot=1)                             # Sub 0-2-2
               + I.U(DART, top=4, bot=2)                            # Dart 4-0-2
               + I.P("e", BOMB, (2, 3, 0))
               # 2-0-0 switches the Heli to Pursuit by itself. Until then it follows the mouse,
               # which rests on its pad; after it, it roams, so its later upgrades rely on the
               # panel staying open (it does across back-to-back steps on one tower)
               + I.P("b", HELI) + I.U(HELI, top=2)
               + I.U(HELI, mid=2)                                   # 2-2-0
               + I.U(HELI, top=1))}                                 # 3-2-0
D.MAULER_SPOTS = []
# The Sniper's right-side panel title reads as nothing to the OCR (as on Muddy Puddles). It stands
# alone, so any panel its click opens is its own; tiers still come off the pips.
I.NAME.pop(repr(SNIPER), None)
I.NAME.pop(repr(OBYN), None)      # his purple skin title ("Mountain Guardian") reads badly too
D.DONE_AFTER = 0
D.NICE = {repr(OBYN): "Obyn", repr(DART): "Dart", repr(SUB): "Sub", repr(SNIPER): "Sniper",
          repr(BOMB): "Bomb", repr(HELI): "Heli"}
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

OBYN_TILE = (103, 414)          # hero list: row 2, column 1
STANDARD_BTN = (640, 560)


def pick_obyn():
    F.click(105, 975)           # Change Hero
    F.wait(2)
    F.click(*OBYN_TILE)
    F.wait(1)
    F.hero_select("Obyn")     # (skips the map if Obyn is locked)
    F.wait(1)
    F.click(78, 55)             # back to the mode screen
    F.wait(2)


F.on_mode_screen = pick_obyn
F.HERO = "Obyn"
F.nav = lambda: F.nav_to("Dark Dungeons", (625, 420), STANDARD_BTN, final=F.IN_GAME)   # Easy, Standard

if __name__ == "__main__":
    F.main()
