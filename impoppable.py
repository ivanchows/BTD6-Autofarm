# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Infernal, Hard, Impoppable. Same menus/overlay/stop keys as farm.py.

Rounds run back to back. "Round X" steps are queued as soon as round X is on screen and
each purchase goes through the moment the cash is there; the boomer is bought mid round 8.
Start it on the home screen, a fresh Impoppable game, or a victory/defeat screen.
Stop: Numpad 0 (or F8).
"""
import sys
import time

import farm as F

SKY_KEY, BOOM_KEY, SNIPER_KEY, VILLAGE_KEY, ALCH_KEY, HERO_KEY = "p", "w", "z", "k", "f", "u"
TARGET_KEY = "\t"   # next targeting priority: First -> Last -> Close -> Strong -> First

SKY1 = (830, 375)
SKY2 = None        # set below (a Spot: the centre rock moves a little)
BOOM = None        # set below (a Spot, like sky2)
BEN = (1190, 815)
VILLAGE = (1582, 488)
ALCH = (1518, 592)
SNIPER_TOP = (1549, 669)   # ends 0-2-5
SNIPER_BOT = (1608, 699)   # ends 5-2-0


class Spot:
    """A tower spot with fallbacks: if placing is refused while the cash is plainly there,
    the next spot is tried, and every later upgrade clicks wherever it really landed."""
    def __init__(self, name, *cands):
        self.name, self.cands, self.i = name, cands, 0

    @property
    def xy(self):
        return self.cands[self.i]

    def __repr__(self):         # stable key for TARGET/NAME/FINAL, whichever spot is used
        return self.name


SNIPER_3 = Spot("sniper3", (1605, 600), (1625, 565), (475, 270))   # island gaps, then top-left pad


SKY2 = Spot("sky2", (870, 710), (870, 725), (875, 740), (865, 765))   # top of the rock (range) first
BOOM = Spot("boom", (800, 720), (800, 735), (795, 760))                # beside it, top first


def xy(pos):
    return pos.xy if isinstance(pos, Spot) else pos

IDLE = [(1812, 1015, (85, 198, 0), 45), (1862, 1015, (85, 197, 0), 45)]   # single "play" arrow
FAST = [(1830, 1015, (171, 247, 5), 30)]                                 # bright fast-forward

# Home -> ... -> Infernal -> Hard -> Impoppable
HARD_BTN = (1290, 420)
IMPOP_BTN = (1280, 740)


def read_cash():
    """Cash top left ('$605'); None if unreadable. An open upgrade panel on the left pushes
    the HUD right (to about x=860), so the box is wide; it stops short of "Cash spent"."""
    im = F.grab()
    c = im.crop((round(330 * F.W / 1920), round(10 * F.H / 1080),
                 round(1000 * F.W / 1920), round(62 * F.H / 1080)))
    for v in (c, c.resize((c.width * 2, c.height * 2))):
        t = F._ocr(v).replace(" ", "").replace(".", ",").upper().replace("O", "0")
        m = F.re.search(r"\$([\d,]+)", t)
        if m:
            return int(m.group(1).replace(",", ""))
    return None


SEL = {"pos": None}     # tower whose upgrade panel is open


def ghost_out(im=None):
    """While a tower is stuck to the mouse for placing, an orange cancel X shows top right."""
    im = im or F.grab()
    return all(abs(im.getpixel(_px(x, 100))[0] - 255) < 20 and abs(im.getpixel(_px(x, 100))[1] - 121) < 40
               and im.getpixel(_px(x, 100))[2] < 50 for x in (1580, 1620))


def drop_ghost():
    """Cancel a tower stuck to the mouse (else the next click drops it somewhere random) by
    clicking that X. Safe: the X only exists while a ghost is out. Esc is not (with nothing
    out it opens the pause menu)."""
    if ghost_out():
        F.click(1580, 100)
        F.wait(0.2)
        return True
    return False


def try_place(key, pos):
    """'placed', 'nocash' or 'blocked', read off the ghost instead of the cash display:
    no ghost after the hotkey = can't afford it yet; ghost gone after the click = placed;
    ghost still out = the spot refused it."""
    drop_ghost()
    if SEL["pos"] is not None:
        deselect()
    x, y = xy(pos)
    F.move(x, y)
    F.key(key)
    F.wait(0.2)
    if not ghost_out():
        return "nocash"
    F.click(x, y)
    for _ in range(4):
        F.wait(0.15)
        if not ghost_out():
            return "placed"
    drop_ghost()
    return "blocked"


def deselect():
    F.click(1000, 1060)
    F.wait(0.05)
    SEL["pos"] = None


def select(pos):
    pos = xy(pos)
    drop_ghost()
    """Open pos's upgrade panel. Stays open across back-to-back upgrades of the same tower;
    a different tower gets a click-off first, so an open panel never covers the next click."""
    if SEL["pos"] == pos:
        return
    if SEL["pos"] is not None:
        deselect()
    F.click(*pos)
    F.wait(0.1)
    SEL["pos"] = pos


# Atomic ops, run strictly in order. A purchase only counts once the cash drops; until then
# it is retried every half second (start-of-round money can lag behind the schedule).
def op_place(key, pos):
    if SEL["pos"] is not None:
        deselect()
    x, y = xy(pos)
    F.move(x, y)
    F.key(key)
    F.wait(0.06)
    F.click(x, y)
    F.wait(0.12)


def op_upgrade(pos, k):
    select(pos)
    F.key(k)
    F.wait(0.1)


def op_tabs(pos, n):
    select(pos)
    for _ in range(n):
        F.key(TARGET_KEY)
        F.wait(0.06)


def _px(x, y):
    return round(x * F.W / 1920), round(y * F.H / 1080)


PANEL_DX = 1222     # a right-side panel sits this far right of a left-side one


def panel_side(im):
    """0 for a left-side upgrade panel, PANEL_DX for a right-side one (towers on the left
    of the map open it on the right), None if no panel. Found by the cyan "i" button and
    the tan frame, not the SELL button: in CHIMPS selling is off and SELL goes dark."""
    for dx in (0, PANEL_DX):
        r, g, b = im.getpixel(_px(70 + dx, 155))
        r2, g2, b2 = im.getpixel(_px(60 + dx, 70))
        if b > 170 and g > 140 and r < 90 and r2 > 160 and g2 > 115 and b2 < 130:
            return dx
    return None


def panel_open(im):
    return panel_side(im) is not None


def tiers(im=None):
    """(top, mid, bot) of the selected tower, counted from the green pips in its panel."""
    dx = None
    for _ in range(4):
        im = im or F.grab()
        dx = panel_side(im)
        if dx is not None:
            break
        F.wait(0.1)
        im = None
    if dx is None:
        return None
    out = []
    for y0, y1 in ((420, 570), (570, 720), (720, 880)):
        runs, on = 0, False
        for y in range(y0, y1):
            r, g, b = im.getpixel(_px(56 + dx, y))
            green = g > 170 and b < 100        # pip greens run into a yellow highlight
            if green and not on:
                runs += 1
            on = green
        out.append(min(runs, 5))
    return tuple(out)


TARGET = {}     # pos -> [top, mid, bot] the schedule has asked for so far
NAME = {}       # pos -> name tokens of the tower that belongs there
# OCR reads these titles loosely ("ISmpeR MOnKey", "ALcnemusTt"): match on fragments
TOKENS = {"p": ("SKY", "WARD"), "w": ("BOOM", "RANG"), "z": ("MPER", "NIPE", "SNIP"),
          "k": ("VILL",), "f": ("ALC", "HEM"), "u": ("BEN", "JAM")}


def selected_is(pos):
    """Is the open panel the tower that belongs at pos? Click areas overlap (the boomer
    spot also hits the skywarden), so never trust the click alone."""
    want = NAME.get(repr(pos))
    if not want:
        return True
    im = F.grab()
    dx = panel_side(im) or 0
    title = F._ocr(im.crop((40 + dx, 55, 420 + dx, 105)).resize((760, 100))).upper()
    return any(t in title for t in want)


def P(key, pos, path=(0, 0, 0)):
    """Place (skipped if a tower already stands there), then upgrade to path."""
    TARGET[repr(pos)] = [0, 0, 0]
    NAME[repr(pos)] = TOKENS[key]
    return [("place", op_place, (key, pos), f"place {key} {pos}")] + U(pos, *path)


def U(pos, top=0, mid=0, bot=0):
    """Raise pos's paths by these amounts; each op is 'path p up to level n', bought only
    while the panel's pips say it is below n, so nothing is ever bought twice or skipped."""
    t = TARGET.setdefault(repr(pos), [0, 0, 0])
    ops = []
    for p, n in ((0, top), (1, mid), (2, bot)):
        for _ in range(n):
            t[p] += 1
            ops.append(("tier", None, (pos, p, t[p]), f"{pos} {'top mid bot'.split()[p]} -> {t[p]}"))
    return ops


def T(pos, mode):
    return [("target", None, (pos, mode), f"targeting {pos} -> {mode}")]


def target_label():
    im = F.grab()
    dx = panel_side(im)
    if dx is None:
        return ""
    return F._ocr(im.crop((120 + dx, 350, 330 + dx, 400)).resize((420, 100))).upper()


# "Round X" steps: queued the moment round X is on screen, each bought as soon as it is
# affordable. 0 = before the first round.
STEPS = {
    0: P(SKY_KEY, SKY1) + P(SKY_KEY, SKY2, (1, 0, 0)),
    8: U(BOOM, bot=1),
    10: U(BOOM, mid=1, bot=1),
    12: U(BOOM, mid=1),
    17: P(SNIPER_KEY, SNIPER_TOP) + T(SNIPER_TOP, "STRONG") + P(SNIPER_KEY, SNIPER_BOT, (1, 0, 0)) + T(SNIPER_BOT, "STRONG"),
    22: P(HERO_KEY, BEN),
    23: U(SNIPER_BOT, mid=1),
    26: U(SNIPER_BOT, mid=1),
    27: U(BOOM, mid=1),
    32: U(SNIPER_TOP, mid=2, bot=2) + T(SNIPER_TOP, "FIRST"),
    35: U(SNIPER_TOP, bot=1),
    38: U(SNIPER_TOP, bot=1),
    42: P(VILLAGE_KEY, VILLAGE, (2, 0, 2)),
    48: U(VILLAGE, bot=1),
    50: U(SNIPER_BOT, top=2),
    55: U(SNIPER_TOP, bot=1),
    58: P(ALCH_KEY, ALCH, (4, 0, 1)),
    68: P(SNIPER_KEY, SNIPER_3, (0, 5, 2)),
    80: U(ALCH, top=1),                                       # 4-0-1 -> 5-0-1
    86: U(SNIPER_BOT, top=2),
}
DURING = {8: P(BOOM_KEY, BOOM)}     # bought mid round 8, as soon as the cash is there

# The most each tower ever gets in the plan: a selected tower already past this on some
# path is the wrong tower (two snipers share a click area), so no key is pressed on it.
FINAL = {}
for _ops in list(STEPS.values()) + list(DURING.values()):
    for _op in _ops:
        if _op[0] == "tier":
            _pos, _p, _lvl = _op[2]
            _f = FINAL.setdefault(repr(_pos), [0, 0, 0])
            _f[_p] = max(_f[_p], _lvl)


def _pos_of(op):
    return repr(op[2][1] if op[0] == "place" else op[2][0])


G = {"round": 0, "done": set(), "during": set(), "last_ocr": 0.0, "pending": None, "fresh": False,
     "queue": [], "last_try": 0.0}


def has_tower(pos):
    select(pos)
    F.wait(0.2)
    if panel_open(F.grab()) and selected_is(pos):
        return True
    deselect()
    return False


def run_queue():
    """Try the first few queued steps, not just the head: a purchase still waiting for cash
    (Ben at $1,295) must not hold back cheaper steps queued behind it. Safe because every
    step checks its own tower and target before acting."""
    if not G["queue"] or time.time() - G["last_try"] < 0.5:
        return
    G["last_try"] = time.time()
    pending_places = set()
    for op in list(G["queue"][:4]):
        # an upgrade/targeting must never run before its tower is placed: an empty spot's
        # click selects whatever stands next to it
        if op[0] != "place" and _pos_of(op) in pending_places:
            continue
        if op[0] == "place":
            pending_places.add(_pos_of(op))
        if try_op(op):
            pending_places.discard(_pos_of(op))
            G["queue"].remove(op)
            G["fails"] = 0
            print(op[3])
    if not G["queue"] and SEL["pos"] is not None:
        deselect()


FAILS = {}   # refused tries per step


def try_op(op):
    kind, fn, args, label = op
    done = False
    if kind == "free":
        fn(*args)
        done = True
    elif kind == "target":
        # Tab until the panel's label reads the wanted mode (no blind press counts)
        pos, mode = args
        select(pos)
        F.wait(0.15)
        if selected_is(pos):
            for _ in range(6):
                if mode in target_label():
                    done = True
                    break
                F.key(TARGET_KEY)
                F.wait(0.25)
        else:
            deselect()
    elif kind == "tier":
        pos, p, level = args
        select(pos)
        F.wait(0.1)
        cur = tiers()
        if cur is not None and not selected_is(pos):
            cur = None                  # some other tower's panel: never press keys on it
            print(f"wrong tower selected for {label}, retrying")
        if cur is None:                 # panel didn't open: click the tower again next try
            deselect()
        elif any(cur[q] > FINAL.get(repr(pos), [5, 5, 5])[q] for q in range(3)):
            print(f"!! {label}: selected tower is {cur}, more than this spot ever gets - not touching it")
            deselect()
        elif cur[p] >= level:
            done = True                 # already there (bought earlier, or a restart)
        else:
            F.key(",./"[p])
            now = None
            for delay in (0.25, 0.35, 0.5):
                F.wait(delay)
                now = tiers()
                if now and now != cur:
                    break
            if now and now != cur and any(now[q] != cur[q] for q in range(3) if q != p):
                print(f"!! wrong path moved for {label}: {cur} -> {now}")
            done = bool(now) and now[p] >= level
    elif kind == "place":
        key, pos = args
        result = try_place(key, pos)
        if result == "placed":
            done = True
        elif result == "blocked":
            FAILS[label] = FAILS.get(label, 0) + 1
            if isinstance(pos, Spot) and FAILS[label] >= len(pos.cands) and key != SNIPER_KEY                     and has_tower(pos):
                done = True     # every spot refused and it's standing there (a restart)
                print("already standing:", label)
            elif isinstance(pos, Spot):
                pos.i = (pos.i + 1) % len(pos.cands)   # the spot refused it: next spot
                print("spot refused, trying", pos.xy)
            elif FAILS[label] >= 3:
                done = True     # refused 3 times at a fixed spot with cash in hand: the tower
                print("already standing:", label)      # is already there (a restart)
    return done


def read_round(im):
    """'ROUND 6/100' top right. OCR likes the label kept in, and mixes up O/0 and l/1."""
    c = im.crop((round(1380 * F.W / 1920), 0, round(1570 * F.W / 1920), round(90 * F.H / 1080)))
    for v in (c, c.resize((c.width * 2, c.height * 2))):
        t = F._ocr(v).upper().replace(" ", "").replace("O", "0").replace("I", "1").replace("L", "1")
        m = F.re.search(r"(\d+)/1\d\d", t)
        if m:
            return int(m.group(1))
    return None


def setup():
    G.update(round=0, done={0}, during=set(), pending=None, fresh=True, queue=list(STEPS[0]))
    FAILS.clear()
    SEL["pos"] = None
    SNIPER_3.i = SKY2.i = BOOM.i = 0
    print("impoppable: start towers")
    for _ in range(40):         # never hang here: the queue keeps going during the rounds
        if not G["queue"]:
            break
        F.check_stop()
        G["last_try"] = 0
        run_queue()
    start_round()


def start_round():
    F.key(" ")
    F.wait(0.3)
    if not F.matches(F.grab(), FAST):
        F.key(" ")


def ingame():
    im = F.grab()
    if F.matches(im, IDLE):         # non-stop: start the next round the moment one ends
        start_round()
        return
    run_queue()
    if time.time() - G["last_ocr"] < 0.5:
        return
    G["last_ocr"] = time.time()
    r = read_round(im)
    if not r or r > 100:
        return
    # take a new round only after two matching reads, and never jump by more than 3
    if r != G["round"]:
        if G["pending"] == r and (G["round"] == 0 or 0 < r - G["round"] <= 3):
            if G["round"] == 0 and not G["fresh"]:
                # joined mid-game: every place/upgrade is safe to repeat (it checks the
                # tower first), so re-run all of them; only targeting presses are skipped
                past = [x for x in sorted(set(STEPS) | set(DURING)) if x < r]
                for x in past:
                    # placements were done when the game was first played; re-checking
                    # them is slow (it lost a game) - re-check only upgrades and targeting
                    G["queue"] += [op for op in DURING.get(x, []) + STEPS.get(x, []) if op[0] != "place"]
                G["done"] = {x for x in STEPS if x < r}
                G["during"] = {x for x in DURING if x <= r}
            G["round"] = r
            F.STATS["status"] = f"round {r}"
            F.STATS["progress"] = time.time()     # keeps the watchdog's stall timer quiet
            print("round", r)
        G["pending"] = r
        return
    for x in sorted(set(DURING) | set(STEPS)):
        if x in DURING and r >= x and x not in G["during"]:
            G["during"].add(x)
            G["queue"] += DURING[x]
        if x in STEPS and r >= x and x not in G["done"]:
            G["done"].add(x)
            G["queue"] += STEPS[x]
            print("round", x, "steps queued")


def on_defeat(im):
    """Log every loss for debugging: round, what was still queued, and a screenshot."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    folder = F.os.path.join(F.os.path.dirname(F.os.path.abspath(__file__)), "losses")
    F.os.makedirs(folder, exist_ok=True)
    im.save(F.os.path.join(folder, f"{stamp}_round{G['round']}.png"))
    pending = "; ".join(op[3] for op in G["queue"]) or "nothing"
    with open(F.os.path.join(folder, "losses.log"), "a", encoding="utf-8") as f:
        f.write(f"{stamp} lost on round {G['round']}, still queued: {pending}\n")


BEN_REF = F.os.path.join(F.os.path.dirname(F.os.path.abspath(__file__)), "ben_portrait.png")
HERO_BOX = (20, 900, 200, 1075)     # the hero portrait, bottom left of the mode screen
BEN_TILE = (405, 410)               # hero list: always 2nd row, last (3rd) column
SELECT_BTN = (1110, 615)            # green Select under the hero


def hero_is_ben():
    from PIL import ImageChops, ImageStat
    ref = F.Image.open(BEN_REF).convert("RGB")
    cur = F.grab().crop(HERO_BOX).convert("RGB").resize(ref.size)
    return sum(ImageStat.Stat(ImageChops.difference(ref, cur)).mean) / 3 < 25


def ensure_ben():
    """On the mode screen: if the hero isn't Benjamin, open Change Hero, pick him, come back."""
    if hero_is_ben():
        return
    print("hero is not Benjamin: switching")
    F.click(105, 975)                   # Change Hero
    F.wait(2)
    F.click(*BEN_TILE)
    F.wait(1)
    F.click(*SELECT_BTN)
    F.wait(1)
    F.click(78, 55)                     # back to the mode screen
    F.wait(2)
    print("hero is Benjamin now" if hero_is_ben() else "!! could not confirm Benjamin")


F.on_mode_screen = ensure_ben
F.on_defeat = on_defeat
F.setup = setup
F.ingame = ingame
if IMPOP_BTN:
    F.NAV = F.NAV[:4] + [(HARD_BTN, F.MODE), (IMPOP_BTN, F.DEFLATION_POPUP)]

if __name__ == "__main__":
    F.main()
