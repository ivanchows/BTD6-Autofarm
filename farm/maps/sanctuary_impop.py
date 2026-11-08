# /// script
# dependencies = ["mss", "pillow", "numpy", "opencv-python-headless",
#                 "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Sanctuary, Hard, Impoppable, hero Obyn. Runs on dark_castle_impop.py's machinery.

Sanctuary's platforms move after every round, so no tower has a fixed spot. Measured in Sandbox
(2026-11-04, rounds 6-30):
  - the temple at the top sits at one of 3 places: (0,0), (-143,-18) or (+145,-18) from home;
  - the bottom platform at one of 2: (0,0) or (+159,0);
  - the 4 round outer platforms wander all over.
So: temple and bottom towers = a fixed offset from the temple/bottom, whose shift is found live
by matching saved crops (sanctuary/*.png); Desperados and Snipers on the outer platforms are
found live by colour (hat brown, helmet green), and placed on outer platforms found by the
colour of their stone tops.
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import os
import time

import cv2
import numpy as np

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I
import dark_castle_impop as D

HERE = os.path.dirname(os.path.abspath(__file__))
REF = {n: cv2.imread(os.path.join(HERE, "sanctuary", n + ".png")) for n in
       ("temple_left", "temple_right", "bottom_side")}
REF_AT = {"temple_left": (630, 120), "temple_right": (975, 140), "bottom_side": (650, 1050)}
TEMPLE_SHIFTS = [(0, 0), (-143, -18), (145, -18)]
BOTTOM_SHIFTS = [(0, 0), (159, 0)]
TEMPLE_HOME, BOTTOM_HOME = (830, 200), (760, 960)


def screen():
    """The map as a 1920x1080 BGR array (an upgrade panel can cover towers: callers close it)."""
    a = np.asarray(F.grab().convert("RGB"))[:, :, ::-1]
    if a.shape[1] != 1920:
        a = cv2.resize(a, (1920, 1080))
    return a


def _score(a, name, dx, dy):
    t = REF[name]
    x, y = REF_AT[name]
    x, y = x + dx, y + dy
    if x < 0 or y < 0 or y + t.shape[0] > a.shape[0] or x + t.shape[1] > a.shape[1]:
        return -1
    return float(cv2.matchTemplate(a[y:y + t.shape[0], x:x + t.shape[1]], t, cv2.TM_CCOEFF_NORMED)[0][0])


def temple_shift(a=None):
    a = screen() if a is None else a
    return max(TEMPLE_SHIFTS, key=lambda s: _score(a, "temple_left", *s) + _score(a, "temple_right", *s))


def bottom_shift(a=None):
    a = screen() if a is None else a
    return max(BOTTOM_SHIFTS, key=lambda s: _score(a, "bottom_side", *s))


def blobs(a, rgb, tol, amin, amax, close=0, merge=0):
    m = (np.abs(a.astype(int) - np.array(rgb[::-1])).max(2) <= tol).astype(np.uint8)
    m[:, 1640:] = 0
    if close:
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    n, _, st, cen = cv2.connectedComponentsWithStats(m)
    pts = [[float(cen[i][0]), float(cen[i][1]), int(st[i, 4])] for i in range(1, n) if amin <= st[i, 4] <= amax]
    if merge:       # one sprite can break into parts (a hat's brim and crown)
        out = []
        for x, y, w in sorted(pts, key=lambda p: -p[2]):
            for o in out:
                if abs(o[0] - x) < merge and abs(o[1] - y) < merge:
                    o[2] += w
                    break
            else:
                out.append([x, y, w])
        pts = out
    return pts


def _not_temple(p, a):
    dx, dy = temple_shift(a)
    return abs(p[0] - (TEMPLE_HOME[0] + dx)) > 260 or p[1] > 330


def hats(a):
    return [(round(x), round(y)) for x, y, w in blobs(a, (170, 81, 19), 18, 600, 6000, merge=30)
            if w >= 2200 and _not_temple((x, y), a)]


def helmets(a):
    """Sniper helmets: dark green (r 60-110, g 110-160). The green pets are far brighter (g>200)."""
    b = a.astype(int)
    m = ((b[..., 2] >= 60) & (b[..., 2] <= 110) & (b[..., 1] >= 110) & (b[..., 1] <= 160)
         & (b[..., 0] >= 22) & (b[..., 0] <= 66)).astype(np.uint8)
    m[:, 1640:] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, _, st, cen = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w = float(cen[i][0]), float(cen[i][1]), int(st[i, 4])
        if 700 <= w <= 9000 and _not_temple((x, y), a):
            if w > 3400:            # two helmets side by side read as one blob
                out += [(round(x) - 30, round(y)), (round(x) + 30, round(y))]
            else:
                out.append((round(x), round(y)))
    return out


def platforms(a):
    """Centres of the outer platforms' stone tops (not the temple, not the bottom platform)."""
    tdx, tdy = temple_shift(a)
    bdx, bdy = bottom_shift(a)
    out = []
    for x, y, w in blobs(a, (122, 118, 40), 22, 8000, 80000, close=9):
        if abs(x - (TEMPLE_HOME[0] + tdx)) < 220 and y < 380:
            continue
        if abs(x - (BOTTOM_HOME[0] + bdx)) < 160 and y > 860:
            continue
        out.append((round(x), round(y)))
    return out


def _near(p, pts, d):
    return any(abs(p[0] - q[0]) < d and abs(p[1] - q[1]) < d for q in pts)


class Fixed(I.Spot):
    """A tower on the temple or the bottom platform: home point + that platform's live shift."""
    def __init__(self, name, home, where):
        super().__init__(name, home)
        self.home, self.where = home, where

    @property
    def xy(self):
        dx, dy = (temple_shift if self.where == "temple" else bottom_shift)()
        return (self.home[0] + dx, self.home[1] + dy)


PICK = {}           # name -> which detected sprite to try next (cycles on a wrong panel)


class Outer(I.Spot):
    """A Desperado or Sniper on an outer platform. Before it stands, xy is where to place it;
    after, xy is one of the live-detected sprites of its kind (cycled by PICK on a mismatch)."""
    def __init__(self, name, kind, idx):
        super().__init__(name, (0, 0), (0, 0), (0, 0), (0, 0), (0, 0))
        self.kind, self.idx = kind, idx
        self.placed = False     # set when its place step succeeds (or on a rejoin past it)

    @property
    def xy(self):
        a = screen()
        sprites = (hats if self.kind == "desp" else helmets)(a)
        if self.placed and sprites:                      # it stands: click its sprite
            sprites.sort()
            p = sprites[PICK.get(self.name, 0) % len(sprites)]
            return (p[0], p[1] + 12)
        plats = platforms(a)
        h, s = hats(a), helmets(a)
        if self.kind == "desp":
            free = [p for p in plats if not _near(p, h, 140) and not _near(p, s, 140)]
            if not free:
                return (0, 0)
            p = min(free, key=lambda q: q[1])            # the top-most free platform
            return p
        if self.idx == 0:                                # Sniper 1: bottom-right free platform
            free = [p for p in plats if not _near(p, h, 140) and not _near(p, s, 140)]
            if not free:
                return (0, 0)
            return max(free, key=lambda q: q[0] + q[1])
        # Sniper 2: beside Sniper 1, on its platform (a refused point steps to the next)
        if not s or not plats:
            return (0, 0)
        p = min(plats, key=lambda q: (q[0] - s[0][0]) ** 2 + (q[1] - s[0][1]) ** 2)
        dx, dy = [(70, 10), (-70, 10), (0, 55), (65, -40), (-65, -40)][self.i % 5]
        return (p[0] + dx, p[1] + dy)


# --- the build ------------------------------------------------------------------------------
D1, D2 = Outer("Desperado 1", "desp", 0), Outer("Desperado 2", "desp", 1)
S1, S2 = Outer("Sniper 1", "snip", 0), Outer("Sniper 2", "snip", 1)
OBYN = Fixed("Obyn", (830, 275), "temple")
WIZ = Fixed("Wizard", (750, 265), "temple")
GLUE = Fixed("Glue", (905, 255), "temple")
ALCH2 = Fixed("Alchemist 2", (915, 175), "temple")
VIL2 = Fixed("Village 2", (814, 155), "temple")
VIL1 = Fixed("Village 1", (715, 1000), "bottom")
SPIKE = Fixed("Spike Factory", (770, 925), "bottom")
ALCH1 = Fixed("Alchemist 1", (815, 985), "bottom")

D.FUZZ["AUTOMATIC"] = ("AUTO", "OMAT", "MATIC")
I.TOKENS.update(u=("OBYN", "GREEN", "MOUNT", "GUARD"), a=("WIZ", "ZARD"), y=("GLUE", "GUNN"),
                k=("VILL",), j=("SPIKE", "FACT"), f=("ALC", "HEM"), z=("MPER", "NIPE", "SNIP"),
                **{";": ("DESP", "PERAD")})

D.PRE = I.P(";", D1) + I.P(";", D2)                               # before round 6
I.STEPS = {
    0: [],
    7: I.T(D1, "STRONG"),
    8: I.P("z", S1),
    9: I.T(S1, "STRONG"),
    10: I.P("z", S2) + I.T(S2, "STRONG"),
    14: I.P("u", OBYN),
    15: I.P("a", WIZ, (1, 0, 0)),
    17: I.U(WIZ, top=1),
    19: I.U(WIZ, bot=1),
    20: I.U(WIZ, bot=1),
    21: I.U(S1, top=1) + I.T(S2, "FIRST"),
    22: I.U(S2, top=1) + I.T(S2, "STRONG"),
    28: I.U(WIZ, top=1),                                           # 3-0-2
    31: I.P("k", VIL1),
    32: I.U(VIL1, bot=1),
    33: I.U(VIL1, bot=1),
    35: I.P("j", SPIKE, (0, 0, 1)),
    36: I.U(SPIKE, bot=1) + I.T(SPIKE, "AUTOMATIC"),
    37: I.U(SPIKE, top=1, bot=1),                                  # 1-0-3
    38: I.P("f", ALCH1, (2, 0, 0)),
    39: I.U(ALCH1, top=1),
    42: I.U(ALCH1, top=1),
    45: I.U(SPIKE, bot=1),                                         # 1-0-4
    50: I.U(WIZ, top=1),                                           # 4-0-2
    51: I.P("k", VIL2, (3, 0, 0)),
    53: I.U(VIL2, top=1, bot=2),                                   # 4-0-2
    54: I.P("y", GLUE, (2, 1, 0)),
    55: I.U(GLUE, top=1, mid=1),
    58: I.U(GLUE, top=1),
    78: I.U(WIZ, top=1),                                           # 5-0-2
    85: I.U(SPIKE, bot=1) + I.U(VIL1, top=2),                      # 1-0-5, 2-0-2
    94: I.U(GLUE, top=1),                                          # 5-2-0
    95: I.P("f", ALCH2, (4, 2, 0)),
}
I.DURING = {}
ABILITIES = [(22, 1, "1"), (25, 1, "1"), (27, 1, "1")]           # Obyn's Brambles at the start
D.RETRY = 0.25
D.MAULER_SPOTS = []
D.DONE_AFTER = 95
D.NICE = {s.name: s.name for s in (D1, D2, S1, S2, OBYN, WIZ, GLUE, ALCH2, VIL2, VIL1, SPIKE, ALCH1)}
for _s in (D1, D2, S1, S2, OBYN):       # found by colour / skin title: no title check
    I.NAME.pop(repr(_s), None)
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

# --- selecting a moving tower ------------------------------------------------------------------
SELNAME = {"n": None}
_select = I.select


def select(pos):
    if isinstance(pos, (Outer, Fixed)):
        if SELNAME["n"] == pos.name and I.SEL["pos"] is not None:
            return False                     # its panel is still open: keep it
        if I.SEL["pos"] is not None:
            I.deselect()
        p = pos.xy                           # found with no panel covering the map
        r = _select(p)
        SELNAME["n"] = pos.name
        return r
    SELNAME["n"] = None
    return _select(pos)


EXPECT = {}         # Sniper name -> tiers bought; tells two identical Snipers apart
MISS = {}
_selected_is, _try_op = I.selected_is, I.try_op


def selected_is(pos):
    if isinstance(pos, Outer) and pos.kind == "snip" and pos.name in EXPECT:
        if list(I.tiers() or ()) != EXPECT[pos.name]:
            MISS[pos.name] = MISS.get(pos.name, 0) + 1
            if MISS[pos.name] < 6:
                PICK[pos.name] = PICK.get(pos.name, 0) + 1
                return False
        MISS[pos.name] = 0
        return True
    return _selected_is(pos)


def try_op(op):
    done = _try_op(op)
    if done:
        SELNAME["n"] = SELNAME["n"] if I.SEL["pos"] is not None else None
        if op[0] == "place" and isinstance(op[2][1], Outer):
            op[2][1].placed = True
            if op[2][1].kind == "snip":
                EXPECT[op[2][1].name] = [0, 0, 0]
        elif op[0] == "tier" and isinstance(op[2][0], Outer) and op[2][0].name in EXPECT:
            pos, p, level = op[2]
            EXPECT[pos.name][p] = max(EXPECT[pos.name][p], level)
    return done


I.select, I.selected_is, I.try_op = select, selected_is, try_op
_deselect = I.deselect


def deselect():
    _deselect()
    SELNAME["n"] = None


I.deselect = deselect

# --- abilities (Obyn's Brambles) -----------------------------------------------------------------
FIRED, ROUND_AT = set(), {}
_run_queue, _setup = D.run_queue, D.setup


def run_queue():
    r = I.G["round"]
    ROUND_AT.setdefault(r, time.time())
    for rnd, delay, key in ABILITIES:
        if rnd <= r <= rnd + 1 and (rnd, key) not in FIRED and (r > rnd or time.time() - ROUND_AT[r] >= delay):
            FIRED.add((rnd, key))
            I.drop_ghost()
            F.key(key)
            print(f"round {rnd}: ability {key}")
    _run_queue()


def setup():
    FIRED.clear()
    ROUND_AT.clear()
    EXPECT.clear()
    PICK.clear()
    MISS.clear()
    SELNAME["n"] = None
    for o in (D1, D2, S1, S2):
        o.placed, o.i = False, 0
    _setup()
    r = I.G["round"]
    if r > 7:                   # rejoined mid-game: the outer towers already stand
        D1.placed = D2.placed = True
        S1.placed = r > 8
        S2.placed = r > 10
        for o in (S1, S2):
            if o.placed:
                EXPECT[o.name] = [1 if r > 21 + (o is S2) else 0, 0, 0]


I.run_queue = run_queue
F.setup = setup

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


F.on_mode_screen = pick_obyn
F.HERO = "Obyn"
F.nav = lambda: F.nav_to("Sanctuary", (1290, 420), (1280, 740))     # Hard, Impoppable

if __name__ == "__main__":
    F.main()
