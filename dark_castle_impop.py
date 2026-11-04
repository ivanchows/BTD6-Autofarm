# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Dark Castle, Hard, Impoppable, hero Striker Jones. Built on infernal_impop.py's
checked placing/upgrading (ghost + pips + panel title). Steps are bought strictly in order
("save up"), each the moment the cash is there; rounds run back to back.
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import time

import core as F
import infernal_impop as I

# Placement points, tested in Sandbox 2026-11-03. A tall tower is drawn 25-40 px above the
# point it was placed at, so these sit below where each tower appears on screen.
STRIKER = (795, 445)
DART = (590, 615)
SUB = (1090, 700)
SPIKE = (1010, 440)
ALCH = (1020, 280)
BOMB = (872, 445)
VILLAGE = (860, 350)
MAULERS = [(465, 320), (570, 470), (390, 550), (685, 395), (475, 745)]   # left of the path
MAULER_SPOTS = [I.Spot(f"mauler{i + 1}", xy, (xy[0] - 25, xy[1]), (xy[0], xy[1] + 25))
                for i, xy in enumerate(MAULERS)]

I.TOKENS.update(u=("STRIK", "JONE"), q=("DART",), x=("SUB",), j=("SPIKE", "FACT"),
                e=("BOMB", "SHOOT", "BOM", "OOTE", "GOM"))   # OCR reads "Bomg Suooter"

SPIKE_AIM = (1135, 590)     # bottom right of the Spike Factory's range, on the bridge


def aim_spikes():
    """Smart Spikes: Tab the targeting to Set Target (its label turns into a green button),
    press it, click the aim point. True once done."""
    I.select(SPIKE)
    F.wait(0.3)
    dx = I.panel_side(F.grab())
    if dx is None or not I.selected_is(SPIKE):
        I.deselect()
        return False
    for _ in range(6):
        r, g, b = F.grab().getpixel(I._px(135 + dx, 365))
        if g > 170 and r < 140 and b < 80:
            F.click(220 + dx, 375)
            F.wait(0.4)
            F.click(*SPIKE_AIM)
            F.wait(0.3)
            I.deselect()
            return True
        F.key("	")
        F.wait(0.5)
    I.deselect()
    return False


SPIKE_TARGET = [("aim", None, (SPIKE,), f"spike factory -> set target {SPIKE_AIM}")]
PRE = (I.P("u", STRIKER) + I.T(STRIKER, "STRONG")
       + I.P("q", DART) + I.P("x", SUB))                            # before round 1

# Clicks that open the wrong panel (towers overlap: the main bomb sits on Striker, and a click
# on its placement point opened Striker's panel, three losses on round 41) step through
# nearby points. Every tower gets this, so no click pair can loop forever.
BOMB_CLICKS = [(875, 450), (880, 455), (870, 440), BOMB]   # (875, 450) opened it, 2026-11-03
NUDGES = [(0, 0), (5, 10), (10, -15), (-10, 10), (15, 5), (0, -25)]
WRONG = {}          # repr(pos) -> wrong panels in a row
GIVE_UP = 18        # three passes over the nudges, then the step is dropped (logged)
_select, _selected_is = I.select, I.selected_is


def click_point(pos):
    p = I.xy(pos)
    n = WRONG.get(repr(pos), 0)
    if p == BOMB:
        return BOMB_CLICKS[n % len(BOMB_CLICKS)]
    dx, dy = NUDGES[n % len(NUDGES)]
    return (p[0] + dx, p[1] + dy)


def select(pos):
    return _select(click_point(pos) if isinstance(pos, (tuple, I.Spot)) and repr(pos) in I.NAME else pos)


def selected_is(pos):
    if I.xy(pos) == BOMB:
        # its title read misses often; the only tower its clicks hit by mistake is Striker
        F.wait(0.3)
        im = F.grab()
        dx = I.panel_side(im) or 0
        title = F._ocr(im.crop((40 + dx, 55, 420 + dx, 105)).resize((760, 100))).upper()
        ok = not any(t in title for t in ("STRIK", "JONE"))
    else:
        ok = _selected_is(pos)
    if ok:
        WRONG[repr(pos)] = 0
    else:
        WRONG[repr(pos)] = WRONG.get(repr(pos), 0) + 1
        print(f"wrong panel for {pos} ({WRONG[repr(pos)]}x), next click at {click_point(pos)}")
    return ok


I.select, I.selected_is = select, selected_is

# OCR mangles the targeting label ("STR0NG", "STRONC"): match on fragments
FUZZ = {"STRONG": ("STRO", "TRON", "RONG", "TR0N"), "FIRST": ("FIRS", "IRST")}
_target_label = I.target_label


def target_label():
    t = _target_label().replace("0", "O")
    return t + "".join(" " + m for m, frags in FUZZ.items() if any(f in t for f in frags))


I.target_label = target_label
I.STEPS = {
    0: (I.P("j", SPIKE, (0, 0, 2)) + SPIKE_TARGET + I.U(SPIKE, top=2) + I.U(SPIKE, bot=2)
        + I.P("f", ALCH, (3, 0, 0)) + I.P("e", BOMB, (4, 2, 0))),
    46: (I.P("k", VILLAGE, (3, 0, 0))
         + I.U(SPIKE, bot=1)          # 2-0-5 Perma-Spike, affordable around round 65
         + I.U(BOMB, top=1)           # 5-2-0 Bloon Crush
         # Crush holds the blimps back for ages: 0-3-0 MOAB Maulers end the rounds sooner
         + [op for spot in MAULER_SPOTS for op in I.P("e", spot, (0, 3, 0)) + I.T(spot, "STRONG")]
         # then each one on to 0-4-0 (MOAB Assassin)
         + [op for spot in MAULER_SPOTS for op in I.U(spot, mid=1)]),
}
I.DURING = {}
I.FINAL.clear()
for _op in PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)


DONE_AFTER = 46      # the round the last steps are queued
NICE = {repr(STRIKER): "Striker", repr(DART): "Dart", repr(SUB): "Sub", repr(SPIKE): "Spike Factory",
        repr(ALCH): "Alchemist", repr(BOMB): "Bomb", repr(VILLAGE): "Village",
        **{repr(sp): f"Mauler {i + 1}" for i, sp in enumerate(MAULER_SPOTS)}}


def describe(op):
    """A step in words, for the overlay: 'Bomb 5-2-0', 'place Village'."""
    pos = op[2][1] if op[0] == "place" else op[2][0]
    name = NICE.get(repr(pos), repr(pos))
    if op[0] == "place":
        return f"place {name}"
    if op[0] == "tier":
        # tiers this step reaches: the levels asked for so far, taken from the build order
        want = [0, 0, 0]
        for o in PRE + [x for ops in I.STEPS.values() for x in ops]:
            if o[0] == "tier" and repr(o[2][0]) == repr(pos):
                want[o[2][1]] = max(want[o[2][1]], o[2][2])
                if o is op or o[3] == op[3]:
                    break
        return f"{name} {'-'.join(map(str, want))}"
    if op[0] == "target":
        return f"{name} -> {op[2][1].title()}"
    return f"{name} set target"


def next_text():
    """What the farm buys next: the head of the queue, or the next round's first step
    ('r75: Buccaneer 5-2-0', the round it gets bought from) while it waits for that round; 'done' once nothing is left."""
    if I.G["queue"]:
        return describe(I.G["queue"][0])
    later = sorted(k for k in I.STEPS if k not in I.G["done"] and I.STEPS[k])
    if not later:
        return "done"
    return f"r{later[0]}: {describe(I.STEPS[later[0]][0])}"


RETRY = 0.5         # seconds between tries of a step that is still waiting
TRIES = {}          # step label -> failed tries
MAX_TRIES = {"target": 4, "aim": 4}     # a buy waits for cash, so only these are capped


def run_queue():
    """Strictly in order: the head step waits for its cash, nothing jumps ahead of it.
    Steps that go through run back to back; a failed one waits half a second."""
    G = I.G
    if not G["queue"]:
        F.STATS["next"] = next_text()
    if not G["queue"] or time.time() - G["last_try"] < RETRY:
        return
    for _ in range(8):
        if not G["queue"]:
            break
        op = G["queue"][0]
        key = repr(op[2][1] if op[0] == "place" else op[2][0])
        if WRONG.get(key, 0) >= GIVE_UP:
            # drop every step left for this tower, or the next one loops the same clicks
            dropped = [o for o in G["queue"] if repr(o[2][1] if o[0] == "place" else o[2][0]) == key]
            print(f"!! gave up on {key}: its panel never opened in {GIVE_UP} clicks; "
                  f"skipping {len(dropped)} steps: " + "; ".join(o[3] for o in dropped))
            WRONG[key] = 0
            G["queue"] = [o for o in G["queue"] if o not in dropped]
            I.deselect()
            continue
        if aim_spikes() if op[0] == "aim" else I.try_op(op):
            G["queue"].pop(0)
            TRIES.pop(op[3], None)
            print(op[3])
            continue
        TRIES[op[3]] = TRIES.get(op[3], 0) + 1
        if TRIES[op[3]] >= MAX_TRIES.get(op[0], 10 ** 9):
            print(f"!! gave up on '{op[3]}' after {TRIES[op[3]]} tries, moving on")
            G["queue"].pop(0)
            TRIES.pop(op[3], None)
            continue
        break
    G["last_try"] = time.time()
    F.STATS["next"] = next_text()
    if not G["queue"] and I.SEL["pos"] is not None:
        I.deselect()


def setup():
    I.drop_ghost()
    I.deselect()                # an open panel slides the round counter out of the read box
    F.wait(0.4)
    r = None
    for _ in range(8):          # a passing bloon can spoil one read: try a few before
        r = I.read_round(F.grab())  # deciding this is a brand-new game
        if r:
            break
        F.wait(0.3)
    if r and r > 7:            # Impoppable starts on round 6
        I.FAILS.clear()
        I.SEL["pos"] = None
        if set(I.STEPS) - {0}:
            # A round-by-round build: carry on from this round. Everything scheduled for an
            # earlier round is taken as bought (re-checking ~90 steps took whole rounds and
            # lost a game); the next round's steps go in as usual.
            print(f"dark castle: rejoined on round {r}, carrying on from here")
            I.G.update(round=r, done={k for k in I.STEPS if k < r} | {0}, during=set(),
                       pending=None, fresh=True, queue=[])
        else:
            # The whole build is one list bought as fast as cash allows: re-check it (a
            # place on a spot that's taken is refused 3x and counted as standing).
            print(f"dark castle: rejoined on round {r}, re-checking the build")
            I.G.update(round=r, done={0}, during=set(), pending=None, fresh=True,
                       queue=[op for op in PRE if op[0] != "place"] + list(I.STEPS[0]))
        return
    I.G.update(round=0, done={0}, during=set(), pending=None, fresh=True, queue=list(PRE))
    I.FAILS.clear()
    WRONG.clear()
    TRIES.clear()
    I.SEL["pos"] = None
    for spot in MAULER_SPOTS:
        spot.i = 0
    print("dark castle: striker, dart, sub")
    end = time.time() + 30
    while I.G["queue"] and time.time() < end:
        F.check_stop()
        I.G["last_try"] = 0
        run_queue()
    if I.G["queue"]:
        print("!! not placed before the start:", "; ".join(op[3] for op in I.G["queue"]))
    I.G["queue"] += I.STEPS[0]
    I.start_round()


STRIKER_TILE = (405, 222)       # hero list: row 1, column 3


def pick_striker():
    """On the mode screen: open the hero list, pick Striker Jones, Select, back. Cheap and
    skin-proof, so it runs every game instead of trusting a portrait."""
    F.click(105, 975)           # Change Hero
    F.wait(2)
    F.click(*STRIKER_TILE)
    F.wait(1)
    F.click(*I.SELECT_BTN)
    F.wait(1)
    F.click(78, 55)             # back to the mode screen
    F.wait(2)


I.run_queue = run_queue
F.setup = setup
F.on_mode_screen = pick_striker
F.nav = lambda: F.nav_to("Dark Castle", (1290, 420), (1280, 740))   # Hard, Impoppable
F.NAV = [((958, 945), F.MAP_SELECT), ((1335, 975), F.EXPERT_PAGE), ((1645, 430), F.INFERNAL_PAGE),
         ((960, 580), F.DIFFICULTY), ((1290, 420), F.MODE), ((1280, 740), F.DEFLATION_POPUP)]

if __name__ == "__main__":
    F.main()
