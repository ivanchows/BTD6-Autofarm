# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Flooded Valley, Hard, Impoppable, hero Etienne (the user's CHIMPS strat, 2026-11-08).
Runs on dark_castle_impop.py's machinery: checked placing/upgrading, strict in-order queue.
Spots pointed out by the user (capture_spots.py, 2026-11-08).
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import time

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I
import dark_castle_impop as D


def spot(name, x, y):
    """The user's point first; a tall tower is drawn above where it was placed, so a bit lower next."""
    return I.Spot(name, (x, y), (x, y + 25), (x, y - 20))


MERM1 = spot("merm1", 1119, 485)        # bottom one: ends 4-2-0
MERM2 = spot("merm2", 1106, 378)
MERM3 = spot("merm3", 1023, 225)        # top one
SUB = spot("sub", 999, 761)
ETIENNE = (754, 621)
BUCC = spot("bucc", 1067, 658)
SUB2 = spot("sub2", 1391, 676)
ICE = spot("ice", 1101, 583)            # 0-2-0 before round 40, 0-3-2 at round 60
VILLAGE = spot("village", 1120, 634)    # on the ice's frozen water (needs 0-3-2 Ice)
GLUE = spot("glue", 982, 569)          # needs the 5-2-0 Bucc

I.TOKENS.update(u=("ETN", "ETIEN", "TIENNE"), c=("BUCC", "CCAN", "CANEER"), x=("SUB",),
                o=("MERM", "RMON"), t=("ICE",), k=("VILL",), y=("GLUE", "GUNN"))

D.PRE = I.P("o", MERM1)                                         # before the first round
I.STEPS = {
    0: (I.P("o", MERM2) + I.P("o", MERM3) + I.P("x", SUB) + I.P("u", ETIENNE)
        + I.P("c", BUCC, (1, 0, 0)) + I.U(BUCC, mid=2) + I.U(BUCC, top=1)    # 1-0-0, 1-2-0, 2-2-0
        + I.U(SUB, bot=1) + I.U(SUB, top=2)                                   # 0-0-1, 2-0-1
        + I.U(BUCC, top=1)                                                    # 3-2-0
        + I.U(SUB, bot=3)                                                     # 2-0-4
        + I.P("t", ICE, (0, 2, 0))                                            # Ice 0-2-0
        + I.U(MERM1, top=2, mid=2)),                                          # Mermonkey 1 2-2-0
    40: I.U(BUCC, top=2),                                                     # 4-2-0, 5-2-0
    60: (I.U(ICE, mid=1, bot=2) + I.P("k", VILLAGE, (4, 0, 2)) + I.P("x", SUB2, (2, 4, 0))
         + I.U(SUB2, mid=1)                                                   # 2-5-0
         + I.P("y", GLUE, (0, 2, 4)) + I.T(GLUE, "STRONG")
         + I.U(MERM1, top=2)),                                                # 4-2-0
}
# Abilities: (round, seconds into it, key), pressed as soon as the round is on screen
ABILITIES = [(76, 0, "2"), (78, 0, "2"), (80, 0, "3"), (84, 0, "2"), (94, 0, "2"), (97, 0, "2"),
             (100, 0, "3")]

# Off Impoppable the game ends sooner: Easy (40 rounds) is done after Mermonkey 1 2-2-0,
# Medium (60) after the 5-2-0 Bucc (user, 2026-11-08)
LAST = {"easy": 40, "medium": 60}.get(F.DIFF)
if LAST:
    I.STEPS = {k: v for k, v in I.STEPS.items() if k < LAST}

D.MAULER_SPOTS = []
D.DONE_AFTER = max(I.STEPS)
D.NICE = {repr(MERM1): "Mermonkey 1", repr(MERM2): "Mermonkey 2", repr(MERM3): "Mermonkey 3",
          repr(SUB): "Sub", repr(ETIENNE): "Etienne", repr(BUCC): "Buccaneer", repr(SUB2): "Sub 2",
          repr(ICE): "Ice", repr(VILLAGE): "Village", repr(GLUE): "Glue"}
I.DURING = {}
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

FIRED = set()
ROUND_AT = {}       # round -> when it was first seen
_run_queue = D.run_queue


def run_queue():
    r = I.G["round"]
    ROUND_AT.setdefault(r, time.time())
    for rnd, delay, key in ABILITIES:
        # the counter can skip a round (a panel covering it): a round seen late fires at once
        late = r > rnd
        if rnd <= r <= rnd + 1 and (rnd, key) not in FIRED and (late or time.time() - ROUND_AT[r] >= delay):
            FIRED.add((rnd, key))
            I.drop_ghost()
            F.key(key)
            print(f"round {rnd}: ability {key}")
    if not can_afford_head():
        return
    q = I.G["queue"]
    head = q[0] if q else None
    _run_queue()
    if head is not None and head[0] == "tier" and I.G["queue"] and I.G["queue"][0] is head:
        # not bought: learn its real price off the open panel, then wait on the cash
        v = read_price(head[2][1]) if I.SEL["pos"] is not None else None
        if v:
            PRICE[head[3]] = v
            I.deselect()
    elif head is not None:
        PRICE.pop(head[3], None)


PRICE = {}          # step label -> its upgrade price, read off the panel
CASH = {"t": 0.0, "ok": True}


def can_afford_head():
    """An upgrade waits for its cash, read off the HUD, instead of clicking the tower open twice a
    second (user, 2026-11-08). Placing needs no gate: with no cash the hotkey shows no ghost, no click."""
    q = I.G["queue"]
    if not q or q[0][3] not in PRICE:
        return True
    if time.time() - CASH["t"] < 0.4:
        return CASH["ok"]
    CASH["t"] = time.time()
    cash = I.read_cash()
    CASH["ok"] = cash is None or cash >= PRICE[q[0][3]]
    if not CASH["ok"]:
        F.STATS["next"] = f"{D.next_text()} (${PRICE[q[0][3]]})"
    else:
        PRICE.pop(q[0][3])      # one try at that price; a miss reads it again
    return CASH["ok"]


def read_price(p):
    """The open panel's price for path p ('$1,080'), or None."""
    im = F.grab()
    dx = I.panel_side(im)
    if dx is None:
        return None
    y0 = (522, 672, 822)[p]
    c = im.crop((*I._px(270 + dx, y0 - 8), *I._px(400 + dx, y0 + 40)))
    t = F.num_text(F._ocr(c.resize((c.width * 3, c.height * 3)))).upper().replace("O", "0")
    m = F.re.search(r"\$(\d[\d,]{1,6})", t)
    v = int(m.group(1).replace(",", "")) if m else 0
    return v if 50 <= v <= 200000 else None


_setup = D.setup


def setup():
    FIRED.clear()
    ROUND_AT.clear()
    for s in (MERM1, MERM2, MERM3, SUB, BUCC, SUB2, ICE, VILLAGE, GLUE):
        if isinstance(s, I.Spot):
            s.i = 0
    _setup()


ETIENNE_TILE = (254, 798)       # hero list: row 4, column 2 (as quad_easy.py)


def pick_etienne():
    F.click(105, 975)           # Change Hero
    F.wait(2)
    F.click(*ETIENNE_TILE)
    F.wait(1)
    F.hero_select("Etienne")     # (skips the map if Etienne is locked)
    F.wait(1)
    F.click(78, 55)             # back to the mode screen
    F.wait(2)


I.run_queue = run_queue
F.setup = setup
F.on_mode_screen = pick_etienne
F.nav = lambda: F.nav_to("Flooded Valley", (1290, 420), (1280, 740))   # Hard, Impoppable
F.NAV = [((958, 945), F.MAP_SELECT), ((1335, 975), F.EXPERT_PAGE), ((1385, 580), F.DIFFICULTY),
         ((1290, 420), F.MODE), ((1280, 740), F.DEFLATION_POPUP)]

if __name__ == "__main__":
    F.main()
