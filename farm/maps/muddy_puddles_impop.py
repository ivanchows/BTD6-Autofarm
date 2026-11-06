# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""BTD6 AFK farm: Muddy Puddles, Hard, Impoppable, hero Psi. Adapted from the "EASIEST Muddy
Puddles CHIMPS" guide (no second Boomerang, one Sub fewer in the late pack). Runs on
dark_castle_impop.py's machinery: checked placing/upgrading, in-order queue, loop guards.
Spots in muddy_spots.json (tested in Sandbox 2026-11-03).
Stop: Numpad 0 (or F8). Pause: Numpad 1.
"""
import json
import os
import time

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # core.py is one folder up
import core as F
import infernal_impop as I
import dark_castle_impop as D

SP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "muddy_spots.json"),
                    encoding="utf-8"))
T = tuple
BUCC, BOOM, SUB1, PSI = T(SP["buccaneer"]), T(SP["boomerang"]), T(SP["sub_right_puddle"]), T(SP["psi"])
ALCH, VILL, MERM = T(SP["alchemist"]), T(SP["village"]), T(SP["mermonkey"])
DES_MID, *DES_OUT = [T(p) for p in SP["desperados"]]          # middle one first, then the 4 quadrants
GLUE1, GLUE2 = [T(p) for p in SP["glue_gunners"]]
SUB2, SUB3, *LATE = [T(p) for p in SP["subs_middle_puddle"]]  # user's click order
SNIPER = T(SP["sniper"])     # a fixed spot: a Spot with fallbacks put a second Sniper down on a rejoin
HAND_BTN = (378, 305)       # Boomerang panel: switch throwing hand (+PANEL_DX on the right)

I.TOKENS.update(c=("BUCC", "CCAN", "CANEER"), x=("SUB",), z=("MPER", "NIPE", "SNIP", "SNLP", "NLPE", "IPER", "LPER"), u=("PSI", "SIMB", "PSIM"),
                **{";": ("DESP", "PERAD", "RADO")}, y=("GLUE", "GUNN"), o=("MERM", "RMON"))
D.FUZZ["LAST"] = ("LAS", "AST")

D.PRE = I.P("c", BUCC)                                           # before the first round, on First
I.STEPS = {
    0: I.P("z", SNIPER),                                         # Sniper the moment the cash is there
    8: I.T(SNIPER, "STRONG"),
    9: I.P("w", BOOM) + I.T(BOOM, "LAST") + [("hand", None, (BOOM,), "boomerang -> switch hand")],
    10: I.P("x", SUB1),
    12: I.P(";", DES_MID) + I.T(DES_MID, "STRONG"),
    13: I.P("x", SUB2, (1, 0, 0)),                               # Longer Range
    15: I.U(SUB2, top=1),                                        # Advanced Intel
    18: I.U(SUB2, bot=1),                                        # Twin Guns
    22: I.U(SUB2, bot=1) + I.U(SNIPER, mid=1) + I.U(SNIPER, top=1),   # Airburst Darts; Night Vision (0-1-0) first, then FMJ (1-1-0) (user, 2026-11-05)
    27: I.P("u", PSI) + [("tabs", None, (PSI, 3), "psi -> strong (3 tabs)")],
    30: I.U(SUB2, bot=1),                                        # Triple Guns
    35: I.U(SUB2, bot=1) + I.U(DES_MID, mid=1) + I.P("f", ALCH, (2, 0, 0)),   # APD, Eagle Eye, Acid
    37: I.U(ALCH, top=1) + I.U(ALCH, bot=1),                     # Berserker Brew, Faster Throwing
    40: (I.P("y", GLUE1, (1, 1, 0)) + I.P("y", GLUE2, (1, 1, 0)) + I.T(GLUE2, "LAST")
         + [op for p in DES_OUT for op in I.P(";", p, (0, 1, 0))]
         + I.P("x", SUB3, (2, 0, 1)) + I.U(SUB3, bot=3)),
    47: I.U(ALCH, top=1),                                        # Stronger Stimulant
    49: I.U(BUCC, top=3, mid=2),                                 # Destroyer + Hot Shot
    53: I.U(BUCC, top=1) + I.P("k", VILL, (2, 2, 0)) + I.P("o", MERM, (3, 1, 0)),
    76: I.U(BUCC, top=1),                                        # Carrier Flagship
    83: I.U(SUB2, bot=1),                                        # Sub Commander
    84: I.U(VILL, mid=1) + [op for p in LATE for op in I.P("x", p)],   # MIB, then the late Subs
    87: I.U(LATE[0], top=2, bot=4),
    89: I.U(LATE[1], top=2, bot=4),
    91: I.U(LATE[2], top=2, bot=4),
    94: I.U(LATE[3], top=2, bot=4),
    98: I.U(VILL, mid=1),                                        # Call to Arms
}
# Queue each round's steps one round early: the guide's round is when it must be standing,
# so the cash is spent the moment it's there (the Boomerang has to be down before round 9).
I.STEPS = {max(0, k - 1) if k else 0: v for k, v in I.STEPS.items()}
D.RETRY = 0.25
I.NAME.pop(repr(PSI), None)      # his purple skin title fails the name check; he stands alone
# The Sniper's right-side panel title reads as nothing to the OCR; it stands alone, so any open
# panel after clicking it is its own (tiers are still checked off the pips).
I.NAME.pop(repr(SNIPER), None)
# Abilities: (round, seconds into it, key). Timings from the guide's cues, untested.
ABILITIES = [(76, 10, "2"), (80, 12, "2"), (98, 20, "2"), (100, 8, "3")]

D.MAULER_SPOTS = []
D.DONE_AFTER = 98
D.NICE = {repr(BUCC): "Buccaneer", repr(SNIPER): "Sniper", repr(BOOM): "Boomerang", repr(SUB1): "Sub 1", repr(SUB2): "Sub 2",
          repr(SUB3): "Sub 3", repr(PSI): "Psi", repr(ALCH): "Alchemist", repr(VILL): "Village",
          repr(MERM): "Mermonkey", repr(DES_MID): "Desperado", repr(GLUE1): "Glue 1", repr(GLUE2): "Glue 2",
          **{repr(p): f"Desperado {i + 2}" for i, p in enumerate(DES_OUT)},
          **{repr(p): f"Late Sub {i + 1}" for i, p in enumerate(LATE)}}
I.FINAL.clear()
for _op in D.PRE + [op for ops in I.STEPS.values() for op in ops]:
    if _op[0] == "tier":
        _pos, _p, _lvl = _op[2]
        _f = I.FINAL.setdefault(repr(_pos), [0, 0, 0])
        _f[_p] = max(_f[_p], _lvl)

# The middle-puddle Subs overlap, and every one of them reads "Monkey Sub", so a click can open
# a neighbour. Each Sub's expected tiers are tracked; a panel showing other tiers is the wrong Sub.
CLUSTER = {repr(p) for p in [SUB2, SUB3, *LATE]}
EXPECT = {}
TABBED = set()       # towers whose blind Tab presses are done this game
D.MAX_TRIES["tabs"] = 4
_try_op, _selected_is = I.try_op, I.selected_is


def selected_is(pos):
    ok = _selected_is(pos)
    if ok and repr(pos) in CLUSTER and repr(pos) in EXPECT:
        ok = list(I.tiers() or ()) == EXPECT[repr(pos)]
    return ok


def try_op(op):
    if op[0] == "tabs":
        # Psi's targeting label is white on yellow and the OCR can't read it, so it never
        # matched "Strong" (30 s of Tab presses). From First, Strong is exactly 3 Tabs away.
        pos, n = op[2]
        if repr(pos) in TABBED:     # done already (a rejoined game): 3 more would leave Strong
            return True
        I.select(pos)
        F.wait(0.3)
        if I.panel_side(F.grab()) is None or not I.selected_is(pos):
            I.deselect()
            return False
        for _ in range(n):
            F.key(I.TARGET_KEY)
            F.wait(0.15)
        TABBED.add(repr(pos))
        return True
    if op[0] == "hand":
        pos = op[2][0]
        if "hand" in TABBED:        # a toggle: never press it twice in one game
            return True
        I.select(pos)
        F.wait(0.3)
        dx = I.panel_side(F.grab())
        if dx is None or not I.selected_is(pos):
            I.deselect()
            return False
        F.click(HAND_BTN[0] + dx, HAND_BTN[1])
        F.wait(0.2)
        TABBED.add("hand")
        return True
    done = _try_op(op)
    if done and op[0] == "place":
        EXPECT[repr(op[2][1])] = [0, 0, 0]
    elif done and op[0] == "tier":
        pos, p, level = op[2]
        if repr(pos) in EXPECT:
            EXPECT[repr(pos)][p] = max(EXPECT[repr(pos)][p], level)
    return done


I.selected_is, I.try_op = selected_is, try_op

FIRED = set()
ROUND_AT = {}       # round -> when it was first seen
_run_queue = D.run_queue


def run_queue():
    r = I.G["round"]
    ROUND_AT.setdefault(r, time.time())
    for rnd, delay, key in ABILITIES:
        # the counter can skip a round (a panel covering it): a round seen late fires at once
        late = r > rnd
        if rnd <= r <= rnd + 2 and (rnd, key) not in FIRED and (late or time.time() - ROUND_AT[r] >= delay):
            FIRED.add((rnd, key))
            I.drop_ghost()
            F.key(key)
            print(f"round {rnd}: ability {key}")
    _run_queue()


_setup = D.setup


def setup():
    TABBED.clear()
    FIRED.clear()
    ROUND_AT.clear()
    EXPECT.clear()
    _setup()
    if I.G["round"] > 7:        # rejoined mid-game: Psi was set to Strong when he went down
        TABBED.update({repr(PSI), "hand"})


I.run_queue = run_queue
F.setup = setup

PSI_TILE = (103, 905)       # hero list: row 6, column 1 (only once the list is scrolled down)


def pick_psi():
    F.click(105, 975)       # Change Hero
    F.wait(2)
    F.move(254, 600)
    for _ in range(15):
        F.user32.mouse_event(0x0800, 0, 0, -120 & 0xFFFFFFFF, 0)
        time.sleep(0.05)
    F.wait(1)
    F.click(*PSI_TILE)
    F.wait(1)
    F.hero_select("Psi")     # (skips the map if Psi is locked)
    F.wait(1)
    F.click(78, 55)         # back to the mode screen
    F.wait(2)


F.on_mode_screen = pick_psi
F.nav = lambda: F.nav_to("Muddy Puddles", (1290, 420), (1280, 740))     # Hard, Impoppable

if __name__ == "__main__":
    F.main()
