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
import time
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
        + I.U(SPIKE, top=2)                                      # Spike 2-0-3
        + I.U(ICE1, top=2, bot=3) + I.T(ICE1, "STRONG")          # Ice 1 2-0-3, Strong
        + I.P("t", ICE2) + I.P("t", ICE3) + I.T(ICE3, "STRONG")  # the 2 Ice by the Spike and Silas
        + I.U(ICE1, bot=1)                                       # Ice 1 2-0-4
        + I.P("n", MORTAR, (0, 2, 0)) + [("mortar", None, (MORTAR,), "mortar -> aim under ice 1")]),
    # (Ice 1 at 0-0-0 behind the Spike lost on r37-38; Ice 1 2-0-3 first got Spike 2-0-4 too late, r40;
    #  Spike 2-0-4 before the other 2 Ice lost on r38)
    46: (I.U(SPIKE, bot=1)                                       # Spike 2-0-4
         + I.U(ICE2, mid=3) + I.U(ICE3, bot=3)
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


# --- iced towers ------------------------------------------------------------------------------
# The map ices towers over now and then, and an iced tower can't be upgraded. The queue is
# strictly in order, so one iced tower used to hold up everything behind it (Spike 2-0-4 iced
# while Ice 1 sat at 0-0-0: zebras leaked on round 37-38). An upgrade that fails while its price
# is NOT red (we can afford it) means the tower is iced: let other towers' steps go first.
ICED = {}           # tower key -> when it was last seen iced
ICED_FOR = 8        # seconds a tower counts as iced before it's tried again
ICED_AFTER = 3      # affordable-but-failed tries in a row before it counts as iced
STREAK = {}


def _price_red(p):
    """Is the open panel's price for path p red (can't afford it)?"""
    im = F.grab()
    dx = I.panel_side(im)
    if dx is None:
        return None
    y0 = (522, 672, 822)[p]
    red = 0
    for x in range(280 + dx, 390 + dx, 2):
        for y in range(y0, y0 + 32, 2):
            r, g, b = im.getpixel(I._px(x, y))[:3]
            red += r > 190 and g < 90 and b < 90
    return red > 40


def _key(op):
    return repr(op[2][1] if op[0] == "place" else op[2][0])


def try_op(op):
    """'mortar': open its panel, press Set Target, click the aim point under Ice 1."""
    if op[0] == "tier":
        done = _try_op(op)
        k = _key(op)
        if not done and I.SEL["pos"] is not None and _pkey(op) not in PRICE:
            v = _read_price(op[2][1])
            cash = I.read_cash()
            # only a price we couldn't pay is believable: red on the panel and above the cash
            if v and _price_red(op[2][1]) and (cash is None or v > cash):
                PRICE[_pkey(op)] = (v, time.time())
                print(f"{op[3]}: costs ${v}, waiting for the cash")
        if done or I.SEL["pos"] is None or _price_red(op[2][1]) is not False:
            STREAK[k] = 0               # bought, no panel, or can't afford: not iced
        else:
            STREAK[k] = STREAK.get(k, 0) + 1
            if STREAK[k] >= ICED_AFTER:     # one miss is often just timing: need a few in a row
                if k not in ICED or time.time() - ICED[k] > ICED_FOR:
                    print(f"{D.NICE.get(k, k)} looks iced: other towers go first")
                ICED[k] = time.time()
                STREAK[k] = 0
        return done
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
_run_queue = I.run_queue


# --- wait for the cash instead of clicking -----------------------------------------------------
# Impoppable prices (Medium x 1.2). Upgrade prices are read off the panel the first time a buy
# fails, then the step just watches the cash and only clicks once there is enough.
PLACE_PRICE = {"t": 480}       # Ice, as the shop shows it here
PRICE = {}          # step key -> (price, when it was read)
PRICE_FOR = 20      # seconds a read price is trusted


def _pkey(op):
    return (_key(op), op[2][1], op[2][2]) if op[0] == "tier" else None


def price_of(op):
    if op[0] == "place":
        return PLACE_PRICE.get(op[2][0])
    if op[0] == "tier":
        got = PRICE.get(_pkey(op))
        if got and time.time() - got[1] > PRICE_FOR:
            PRICE.pop(_pkey(op), None)  # a misread price must not hold a step for good:
            return None                 # click again now and then, and read it fresh
        return got and got[0]
    return None


def _read_price(p):
    """The open panel's price for path p ('$1,080'), or None."""
    im = F.grab()
    dx = I.panel_side(im)
    if dx is None:
        return None
    y0 = (522, 672, 822)[p]
    c = im.crop((*I._px(270 + dx, y0 - 8), *I._px(400 + dx, y0 + 40)))
    t = F._ocr(c.resize((c.width * 3, c.height * 3))).replace(" ", "").replace(".", ",").upper()
    t = t.replace("O", "0")
    m = F.re.search(r"\$(\d[\d,]{1,6})", t) or F.re.search(r"(\d[\d,]{1,6})", t)
    if not m:
        return None
    s = m.group(1)
    if "$" not in t and "," not in s and len(s) >= 4:
        s = s[1:]               # '$420' read as '4420': the $ came out as a digit
    v = int(s.replace(",", ""))
    return v if 50 <= v <= 200000 else None


# A restart mid-game re-queues upgrades but no placements (infernal_impop's round handler), so
# a tower bought after the restart point (the Mortar) never went down. Before the first step
# on a tower, check it stands; if not, put its placement in front.
PLACE_OP = {repr(op[2][1]): op for ops in I.STEPS.values() for op in ops if op[0] == "place"}
CHECKED = set()


def _ensure_placed(q):
    op = q[0]
    if op[0] == "place":
        CHECKED.add(_key(op))
        return
    k = _key(op)
    if k in CHECKED or k not in PLACE_OP or PLACE_OP[k][2][0] == "u":
        return
    CHECKED.add(k)
    if any(o[0] == "place" and _key(o) == k for o in q):
        return
    if not I.has_tower(I.G["queue"][0][2][0]):
        print(f"{D.NICE.get(k, k)} isn't standing: placing it first")
        q.insert(0, PLACE_OP[k])


def run_queue():
    """While the head step's tower is iced, move the first step for a tower that isn't iced
    to the front (its own order kept), so the cash goes where it can be spent. A step whose
    price is known waits, without clicking, until the cash covers it."""
    q = I.G["queue"]
    now = time.time()
    iced = {k for k, t in ICED.items() if now - t < ICED_FOR}
    if q and _key(q[0]) in iced:
        for i, op in enumerate(q):
            if _key(op) not in iced:
                q.insert(0, q.pop(i))
                break
    if q and now - I.G["last_try"] >= D.RETRY:
        _ensure_placed(q)
        price = price_of(q[0])
        if price:
            cash = I.read_cash()
            if cash is not None and cash < price:
                I.G["last_try"] = now
                F.STATS["next"] = f"{D.next_text()} (${cash}/${price})"
                return
    _run_queue()


I.run_queue = run_queue

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


def setup():
    """A rejoin used to take every earlier step as bought, so a game the farm missed rounds of
    lost with nothing queued. Re-check them: a tier already there and a tower already standing
    are passed over, and prices gate the rest."""
    D.setup()
    r = I.G.get("round") or 0
    if r > 7 and not I.G["queue"]:
        ops = [op for k in sorted(I.STEPS) if k < r for op in I.STEPS[k]]
        # one check per tower path, at the highest level it should have by now (a tier step
        # keeps buying until it's there), instead of walking every single tier from the Ninja on
        top = {}
        for op in ops:
            if op[0] == "tier":
                top[(repr(op[2][0]), op[2][1])] = op
        keep = set(map(id, top.values()))
        # the hero is always down by now, and its check clicks a spot Ice 2 crowds (it stuck)
        I.G["queue"] = [op for op in ops if (op[0] != "tier" or id(op) in keep)
                        and not (op[0] == "place" and op[2][0] == "u")]
        print(f"glacial: re-checking {len(I.G['queue'])} earlier steps")


F.setup = setup
F.on_mode_screen = pick_silas
F.nav = lambda: F.nav_to("Glacial Trail", (1290, 420), (1280, 740))     # Hard, Impoppable

if __name__ == "__main__":
    F.main()
