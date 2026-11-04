# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Tricky Tracks, Easy, Standard (40 rounds), hero Quincy. Runs on dark_castle_impop.py's
machinery (checked placing/upgrading, in-order queue, loop guards, overlay Next line).
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import core as F
import infernal_impop as I
import dark_castle_impop as D

# Read off the user's game 2026-11-04 (towers draw ~25 px above their point); not tested in
# Sandbox. Plain points, not Spots: a Sniper Spot never counts a refused point as "already
# standing", so a rejoined game would retry it forever.
QUINCY = (910, 600)          # 575 was refused
SNIPER_R = (845, 625)
SNIPER_L = (785, 665)

I.TOKENS.update(u=("QUIN", "UINCY", "CYBER"), z=("MPER", "NIPE", "SNIP", "IPER"))

D.PRE = I.P("u", QUINCY)
I.STEPS = {0: (I.P("z", SNIPER_R, (0, 0, 1))
               + I.U(SNIPER_R, top=1, bot=1)                        # right 1-0-2
               + I.P("z", SNIPER_L, (0, 0, 2))
               + I.U(SNIPER_L, mid=2)                               # left 0-2-2
               + I.U(SNIPER_L, bot=2)                               # left 0-2-4
               + I.U(SNIPER_R, bot=2))}                             # right 1-0-4
D.MAULER_SPOTS = []
D.DONE_AFTER = 0
D.NICE = {repr(QUINCY): "Quincy", repr(SNIPER_R): "right Sniper", repr(SNIPER_L): "left Sniper"}
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

# The two Snipers stand side by side and share a title (which the OCR often can't read anyway),
# so a click can open the other one. Each one's bought tiers are tracked; a panel showing other
# tiers is the neighbour, and gets nudged past by the loop guard.
for _s in (QUINCY, SNIPER_R, SNIPER_L):
    I.NAME.pop(repr(_s), None)
EXPECT = {}
_try_op = I.try_op
_selected_is = I.selected_is


def selected_is(pos):
    if repr(pos) in EXPECT:
        return list(I.tiers() or ()) == EXPECT[repr(pos)]
    return _selected_is(pos)


def try_op(op):
    done = _try_op(op)
    if done and op[0] == "place" and repr(op[2][1]) != repr(QUINCY):
        EXPECT[repr(op[2][1])] = [0, 0, 0]
    elif done and op[0] == "tier" and repr(op[2][0]) in EXPECT:
        pos, p, level = op[2]
        EXPECT[repr(pos)][p] = max(EXPECT[repr(pos)][p], level)
    return done


I.selected_is, I.try_op = selected_is, try_op
_setup = D.setup


def setup():
    EXPECT.clear()
    _setup()


F.setup = setup

QUINCY_TILE = (103, 222)        # hero list: row 1, column 1
STANDARD_BTN = (640, 560)


def pick_quincy():
    F.click(105, 975)           # Change Hero
    F.wait(2)
    F.click(*QUINCY_TILE)
    F.wait(1)
    F.click(*I.SELECT_BTN)
    F.wait(1)
    F.click(78, 55)             # back to the mode screen
    F.wait(2)


F.on_mode_screen = pick_quincy
F.nav = lambda: F.nav_to("Tricky Tracks", (625, 420), STANDARD_BTN, final=F.IN_GAME)   # Easy, Standard

if __name__ == "__main__":
    F.main()
