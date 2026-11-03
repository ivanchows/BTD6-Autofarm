# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Flooded Valley, Easy, Deflation. Same menus/overlay/stop keys as core.py.
Every placement and upgrade is checked (ghost + pips, from infernal_impop.py): cash is exact,
$5 left over, so nothing may be missed.
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import time

import core as F
import infernal_impop as I

BUC_KEY, SUB_KEY, WIZARD_KEY = "c", "x", "a"
BUC = I.Spot("buc", (1110, 520), (1125, 530), (1140, 540))
SUB = I.Spot("sub", (1000, 755), (1010, 765), (1020, 775))
WIZARD = I.Spot("wizard", (745, 415), (735, 425), (725, 435))
FLOODED_TILE = (1385, 580)     # first Expert page, bottom right
I.TOKENS.update(c=("BUCC", "CCAN"), x=("SUB",), a=("WIZ", "ZARD"))


def place(key, spot):
    """Back to 'placed' only: a refused spot moves to the next one, a missed key retries."""
    for _ in range(15):
        F.check_stop()
        result = I.try_place(key, spot)
        print("place", spot, spot.xy, result)
        if result == "placed":
            return True
        if result == "blocked":
            spot.i = (spot.i + 1) % len(spot.cands)
        F.wait(0.2)
    print("!! could not place", spot)
    return False


def upgrade(spot, path):
    """Buy up to path, read back off the pips."""
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


def tower(key, spot, path):
    I.NAME[repr(spot)] = I.TOKENS[key]
    if place(key, spot):
        upgrade(spot, path)


def setup():
    print("placing towers")
    I.SEL["pos"] = None
    BUC.i = SUB.i = WIZARD.i = 0
    tower(BUC_KEY, BUC, (4, 2, 0))
    I.start_round()
    tower(SUB_KEY, SUB, (4, 2, 0))
    tower(WIZARD_KEY, WIZARD, (2, 0, 4))
    print("running, cash", I.read_cash())


F.setup = setup
F.nav = lambda: F.nav_to("Flooded Valley", (625, 420), (1280, 450))   # Easy, Deflation
F.ingame = lambda: None
F.on_mode_screen = lambda: None
F.NAV = [((958, 945), F.MAP_SELECT), ((1335, 975), F.EXPERT_PAGE), (FLOODED_TILE, F.DIFFICULTY),
         ((625, 420), F.MODE), ((1280, 450), F.DEFLATION_POPUP)]

if __name__ == "__main__":
    F.main()
