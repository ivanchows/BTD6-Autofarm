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

# One list, bought strictly in order, each step the moment the cash covers it (round numbers
# stopped fitting once the order changed: Perma-Spike landed on r73, not r68).
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
        + I.P("n", MORTAR, (0, 2, 0)) + [("mortar", None, (MORTAR,), "mortar -> aim under ice 1")]
        # (Ice 1 at 0-0-0 behind the Spike lost on r37-38; Ice 1 2-0-3 first got Spike 2-0-4 too
        #  late, r40; Spike 2-0-4 before the other 2 Ice lost on r38)
        + I.U(SPIKE, bot=1)                                      # Spike 2-0-4
        + I.U(ICE2, mid=3) + I.U(ICE3, bot=3)
        + I.U(ICE2, top=2, mid=1) + I.U(ICE3, top=2, bot=1)      # 2-4-0 and 2-0-4
        + I.U(SPIKE, bot=1)                                      # Perma-Spike 2-0-5
        + I.U(ICE1, bot=1)                                       # Icicle Impale 2-0-5
        + I.U(ICE3, bot=1)                                       # second Icicle Impale
        + I.U(ICE2, mid=1)                                       # Absolute Zero 2-5-0
        + I.U(MORTAR, top=2, mid=2)),                            # Mortar 2-4-0
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


def select_point(pos):
    return ICE2_CLICK if I.xy(pos) == ICE2 else pos


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
    if op[0] in ("tier", "place") and price_of(op) is None:
        v0 = None
        if op[0] == "tier":
            # read the price off the panel BEFORE buying: the cash drop alone came out low
            # (pops pay out while it buys: Ice 1 2-0-1 was saved as $95)
            select(op[2][0])
            F.wait(0.15)
            if I.panel_open(F.grab()) and I.selected_is(op[2][0]):
                cur = I.tiers()
                if cur:
                    SEEN[_key(op)] = list(cur)
                v0 = _read_price(op[2][1])
                red, cash = _price_red(op[2][1]), I.read_cash()
                if v0 and cash is not None and red is not None and red == (v0 > cash)                         and (cur is None or cur[op[2][1]] == op[2][2] - 1):
                    _learn(op, v0, "panel")
                    if v0 > cash:
                        return False    # can't afford it: don't press, the cash gate waits
        cash0 = I.read_cash()
        before = SEEN.get(_key(op))
        done = (_try_op if op[0] == "place" else _tier)(op)
        _note_tiers(op)
        cash1 = I.read_cash()
        after = SEEN.get(_key(op))
        # a cash drop counts as the price only if this step really bought it: the tower went
        # up exactly one tier (a re-check of a tier it had paid nothing), or it really placed
        bought = (op[0] == "place" and done and I.FAILS.get(op[3], 0) == 0) or (
            op[0] == "tier" and before is not None and after is not None
            and before[op[2][1]] == op[2][2] - 1 and after[op[2][1]] == op[2][2])
        drop = cash0 - cash1 if cash0 is not None and cash1 is not None else None
        if bought and v0 and drop is not None and v0 <= cash0 and v0 >= drop * 0.8:
            _learn(op, v0, "panel")     # the panel price, checked against what it cost
        elif bought and drop is not None and drop >= 30:
            _learn(op, round(drop * 1.1 / 5) * 5, "paid")    # pops pay out meanwhile: a bit up
        elif not done and op[0] == "tier" and I.SEL["pos"] is not None:
            v = _read_price(op[2][1])
            red = _price_red(op[2][1])
            # believable only if red agrees with it: red exactly when it's above the cash
            if v and cash1 is not None and red is not None and red == (v > cash1):
                _learn(op, v, "panel")
        return done
    if op[0] == "tier":
        done = _tier(op)
        _note_tiers(op)
        if not done and I.SEL["pos"] is not None and _price_red(op[2][1]):
            # cash was at the saved price yet it's red: the saved price is too low. Take the
            # panel's, or anything above the cash now, so it doesn't click again and again
            v, cash = _read_price(op[2][1]), I.read_cash()
            k = _pkey(op)
            if v and cash is not None and v > cash:
                F.set_price(*k, v)
            elif cash is not None:
                F.set_price(*k, max(F.price(*k) or 0, cash + 100))
            print(f"price: {' '.join(map(str, k))} was too low, now ${F.price(*k)}")
        return done
    if op[0] != "mortar":
        return _try_op(op)
    return _aim_mortar()


def _tier(op):
    if True:
        done = _try_op(op)
        k = _key(op)
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


def _aim_mortar():
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


# --- progress, so a restart carries on instead of starting over ----------------------------------
# Every finished step's label is saved; a restart in the same game queues only what's left.
# A new game (set up from round 0) clears it.
PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glacial_progress.json")
try:
    DONE = set(json.load(open(PROGRESS_FILE, encoding="utf-8")))
except (OSError, ValueError):
    DONE = set()


def _save_progress():
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(sorted(DONE), f, indent=0)
    except OSError:
        pass


def remaining():
    """Every step of the build not finished yet, in order (the hero is always down by then)."""
    # a placement counts as done once any step on that tower is: the Dart and Ninja (set up
    # before the first save) were re-placed 3 refused clicks each, a whole round apiece
    started = {_key(op) for op in D.PRE + list(I.STEPS[0]) if op[3] in DONE}
    return [op for op in list(I.STEPS[0])
            if op[3] not in DONE and not (op[0] == "place" and (op[2][0] == "u" or _key(op) in started))]


_try_op_g = try_op


def try_op(op):
    # The cash gate lives here too: dark_castle's run_queue runs several steps per call, so a
    # step behind a finished one skipped the gate in run_queue (Perma-Spike clicked at ~$5k)
    price = must_wait(op) if op[0] in ("tier", "place") else None
    if price and not can_afford(price):
        return False
    done = _try_op_g(op)
    if done and op[3] not in DONE:
        DONE.add(op[3])
        _save_progress()
    return done


I.select, I.try_op = select, try_op
_run_queue = I.run_queue


# --- wait for the cash instead of clicking -----------------------------------------------------
# Every price is learned once (the cash drop on a buy, or the panel's price when a buy fails)
# and saved, so a step just watches the cash and clicks only once there is enough. A step
# whose price isn't known yet is tried at most every UNKNOWN_EVERY seconds.
# Prices live in the shared prices.json (core.price), by tower type, so every farm can use them.
UNKNOWN_EVERY = 6
LAST_BLIND = {"t": 0}
TOWER = {repr(DART): "Dart Monkey", repr(NINJA): "Ninja Monkey", repr(SILAS): "Silas",
         repr(ICE1): "Ice Monkey", repr(ICE2): "Ice Monkey", repr(ICE3): "Ice Monkey",
         repr(SPIKE): "Spike Factory", repr(MORTAR): "Mortar Monkey"}


def _pkey(op):
    """(tower, path, tier) for core.price; path and tier None for placing it."""
    if op[0] == "place":
        return (TOWER[_key(op)], None, None)
    if op[0] == "tier":
        return (TOWER[_key(op)], "top mid bot".split()[op[2][1]], op[2][2])
    return None


def _learn(op, v, how):
    k = _pkey(op)
    if k and v and F.price(*k) is None:
        F.set_price(*k, v)
        print(f"price: {' '.join(str(x) for x in k if x)} = ${v} ({how})")


SEEN = {}           # tower key -> its tiers as last read off its panel this run


def _note_tiers(op):
    if op[0] == "tier" and I.SEL["pos"] is not None and (
            repr(I.SEL["pos"]) == _key(op) or I.xy(I.SEL["pos"]) == I.xy(select_point(op[2][0]))):
        cur = I.tiers()
        if cur:
            SEEN[_key(op)] = list(cur)


def price_of(op):
    k = _pkey(op)
    return F.price(*k) if k else None


def can_afford(price):
    """Two cash reads in a row, both at the price and close to each other: one bad read (the
    coin icon taken for a digit) made Perma-Spike's $36,000 look affordable at ~$5,000."""
    a = I.read_cash()
    if a is None or a < price:
        return False
    F.wait(0.1)
    b = I.read_cash()
    return b is not None and b >= price and abs(a - b) <= max(200, a * 0.05)


def must_wait(op):
    """The price to wait for, or None to go ahead. A tier step only waits once its tower's
    panel has shown it below that level: after a restart the farm re-checks tiers it already
    owns, and those must not wait for cash."""
    price = price_of(op)
    if not price:
        return None
    if op[0] == "tier":
        cur = SEEN.get(_key(op))
        if cur is not None and cur[op[2][1]] >= op[2][2]:
            return None         # already there: go ahead, it passes at once
    # (unseen tiers wait too: Ice 2's panel opens via another click point, so its tiers were
    # never noted and it clicked 4x a second at a $9,700 price)
    return price


LAST_CASH = {"v": None}


def _read_price(p):
    """The open panel's price for path p ('$1,080'), or None."""
    im = F.grab()
    dx = I.panel_side(im)
    if dx is None:
        return None
    y0 = (522, 672, 822)[p]
    c = im.crop((*I._px(270 + dx, y0 - 8), *I._px(400 + dx, y0 + 40)))
    LAST_CASH["v"] = I.read_cash()
    t = F._ocr(c.resize((c.width * 3, c.height * 3))).replace(" ", "").replace(".", ",").upper()
    t = t.replace("O", "0")
    m = F.re.search(r"\$(\d[\d,]{1,6})", t) or F.re.search(r"(\d[\d,]{1,6})", t)
    if not m:
        return None
    s = m.group(1).replace(",", "")
    v = int(s)
    if "$" not in t and len(s) >= 4 and LAST_CASH["v"] is not None:
        # '$420' can come out '4420' (the $ read as a digit), but '$4,320' can come out
        # '4320' too. The price's colour settles it: red means above the cash.
        alt = int(s[1:])
        red, cash = _price_red(p), LAST_CASH["v"]
        if red is not None and (red != (v > cash)) and (red == (alt > cash)):
            v = alt
    return v if 50 <= v <= 200000 else None


# --- frozen towers, seen on screen -------------------------------------------------------------
# A frozen tower sits in a pale see-through ice block. Count ice-block pixels over the tower
# (sprites draw above the click point); each tower's own look sets its baseline (Ice Monkeys
# are white and blue themselves), and a big jump over it means frozen.
BASE = {}


def _ice_frac(im, pos):
    x0, y0 = I.xy(pos)
    n = ice = 0
    for x in range(x0 - 30, x0 + 31, 3):
        for y in range(y0 - 50, y0 + 11, 3):
            r, g, b = im.getpixel(I._px(x, y))[:3]
            n += 1
            ice += b > 200 and g > 200 and r > 150 and b - r > 8
    return ice / n


HITS = {}


def frozen(pos, im=None):
    """Measured 2026-11-04: Mortar 0.02 thawed, 0.32 frozen; Spike 0.00 and 0.40. Ice Monkeys
    and snow read 0.1-0.3 on their own, hence the per-tower baseline; two reads in a row."""
    f = _ice_frac(im or F.grab(), pos)
    k = repr(pos)
    BASE[k] = min(BASE.get(k, 0.3), f)
    hit = f >= max(0.28, BASE[k] + 0.22)
    HITS[k] = HITS.get(k, 0) + 1 if hit else 0
    return HITS[k] >= 3          # ~0.75 s in a row: a snow flicker made 2 reads


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
    if any(_key(o) == k and o[3] in DONE for o in D.PRE + list(I.STEPS[0])):
        return                  # saved progress says it's down (the panel check misses some)
    if not I.has_tower(I.G["queue"][0][2][0]):
        print(f"{D.NICE.get(k, k)} isn't standing: placing it first")
        q.insert(0, PLACE_OP[k])


RESUMED = {"done": False}
FROZEN_CHECK = False


def run_queue():
    """While the head step's tower is iced, move the first step for a tower that isn't iced
    to the front (its own order kept), so the cash goes where it can be spent. A step whose
    price is known waits, without clicking, until the cash covers it."""
    if not RESUMED["done"] and "--running" in sys.argv and I.G.get("round"):
        RESUMED["done"] = True      # restarted mid-game: queue only what's left
        if I.G["round"] <= 7:       # a brand-new game: last game's progress means nothing
            DONE.clear()
            _save_progress()
        I.G["queue"] = remaining()
        print(f"glacial: carrying on, {len(I.G['queue'])} steps left")
    q = I.G["queue"]
    now = time.time()
    # The on-screen frozen check is OFF: it read a thawed Spike as frozen (snow next to it
    # scores almost as high as the ice block), and skipping it broke the build order.
    if FROZEN_CHECK and q and now - I.G["last_try"] >= D.RETRY and q[0][0] in ("tier", "target", "mortar"):
        im = F.grab()
        for op in q[:6]:            # look, don't click: mark frozen towers before trying them
            if op[0] in ("tier", "target", "mortar") and frozen(op[2][0], im):
                k = _key(op)
                if k not in ICED or now - ICED[k] > ICED_FOR:
                    print(f"{D.NICE.get(k, k)} is frozen: other towers go first")
                ICED[k] = now
    iced = {k for k, t in ICED.items() if now - t < ICED_FOR}
    if q and _key(q[0]) in iced:
        for i, op in enumerate(q):
            if _key(op) not in iced:
                q.insert(0, q.pop(i))
                break
    if q and now - I.G["last_try"] >= D.RETRY:
        if _key(q[0]) in iced:      # everything left is frozen: wait, don't click
            I.G["last_try"] = now
            return
        _ensure_placed(q)
        price = must_wait(q[0])
        if price:
            if not can_afford(price):
                I.G["last_try"] = now
                F.STATS["next"] = D.next_text()
                return
        elif price_of(q[0]) or (q[0][0] == "tier" and SEEN.get(_key(q[0])) is not None
                                and SEEN[_key(q[0])][q[0][2][1]] >= q[0][2][2]):
            pass                    # already there: it passes at once
        # (a tower whose panel won't confirm used to get "one look" 4x a second: Perma-Spike)
        elif q[0][0] in ("tier", "place") and now - LAST_BLIND["t"] < UNKNOWN_EVERY:
            return                  # price not learned yet: try now and then, not twice a second
        elif q[0][0] in ("tier", "place"):
            LAST_BLIND["t"] = now
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
    """A fresh game clears the saved progress; a rejoin carries on from the first step not
    done yet (it used to re-check every step from the Ninja on, which wasted rounds)."""
    D.setup()
    r = I.G.get("round") or 0
    if r > 7:
        RESUMED["done"] = True
        I.G["queue"] = remaining()
        print(f"glacial: carrying on, {len(I.G['queue'])} steps left")
    else:
        DONE.clear()
        _save_progress()


F.setup = setup
F.on_mode_screen = pick_silas
F.nav = lambda: F.nav_to("Glacial Trail", (1290, 420), (1280, 740))     # Hard, Impoppable

if __name__ == "__main__":
    F.main()
