"""Builds strats.json: each map's build order, read straight out of its farm script, for the app's
STRATS window. The scripts are loaded with a stand-in core (no game, no clicks).
Run it after changing a build:  uv run strats.py
"""
import importlib
import json
import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "strats.json")

# hotkey -> tower (the farm's own hotkeys, settings in the game)
KEYS = {"q": "Dart", "w": "Boomerang", "e": "Bomb", "r": "Tack", "t": "Ice", "y": "Glue", "z": "Sniper",
        "x": "Sub", "c": "Buccaneer", "v": "Ace", "b": "Heli", "n": "Mortar", "m": "Dartling", "a": "Wizard",
        "s": "Super", "d": "Ninja", "f": "Alchemist", "g": "Druid", "h": "Banana Farm", "j": "Spike Factory",
        "k": "Village", "l": "Engineer", "i": "Beast Handler", "p": "Skywarden", "o": "Mermonkey", ";": "Desperado", "u": "Hero"}


class Dummy:
    """Anything core would hand back: callable, falsy, empty, numeric zero."""
    def __call__(self, *a, **k): return Dummy()
    def __getattr__(self, n): return Dummy()
    def __bool__(self): return False
    def __iter__(self): return iter(())
    def __len__(self): return 0
    def __int__(self): return 0
    def __float__(self): return 0.0
    def __index__(self): return 0
    def __add__(self, o): return o
    __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = __truediv__ = __rtruediv__ = __floordiv__ = __add__
    def __lt__(self, o): return False
    __gt__ = __le__ = __ge__ = __lt__
    def __getitem__(self, k): return Dummy()
    def __setitem__(self, k, v): pass
    def __contains__(self, k): return False
    def __hash__(self): return 0
    def __eq__(self, o): return isinstance(o, Dummy)


def fake_core(diff):
    from PIL import Image, ImageOps
    import time as _t
    m = types.ModuleType("core")
    m.__getattr__ = lambda n: Dummy()
    m.re, m.os, m.sys, m.time, m.json = re, os, sys, _t, json
    m.Image, m.ImageOps = Image, ImageOps
    m.W, m.H, m.OX, m.OY = 1920, 1080, 0, 0
    m.DIFF = diff
    m.STATS = {}
    m.HERE = HERE
    return m


def load(script, diff=None):
    """Import maps/<script> fresh with the stand-in core; return its infernal_impop (I) and
    dark_castle_impop (D) modules as the script left them."""
    for name in list(sys.modules):
        if name in ("core", "infernal_impop", "dark_castle_impop", "keys", "mapsig", "pics") or name.startswith("maps."):
            del sys.modules[name]
        elif name == script[:-3]:
            del sys.modules[name]
    sys.modules["core"] = fake_core(diff)
    for stub in ("keys", "mapsig", "pics", "cv2", "numpy", "mss"):
        sys.modules[stub] = types.ModuleType(stub)
        sys.modules[stub].__getattr__ = lambda n: Dummy()
    sys.path[:0] = [os.path.join(HERE, "maps"), HERE]
    try:
        mod = importlib.import_module(script[:-3])
    finally:
        del sys.path[:2]
    return mod, sys.modules.get("infernal_impop"), sys.modules.get("dark_castle_impop")


def describe(mod, I, D):
    """[(round, [line, ...])]: places with their upgrades, merged per tower, round by round."""
    nice = dict(getattr(D, "NICE", {}) or {})
    names = {}

    count = {}

    def name(pos, key=None):
        """Every tower numbered by type in the order placed: Sniper 1, Sniper 2 (user, 2026-11-09).
        The hero by its own name."""
        r = repr(pos)
        if key is None and r not in names:     # placed by a step of its own: its key from the name tokens
            tok = (getattr(I, "NAME", {}) or {}).get(r)
            key = next((k for k, v in (getattr(I, "TOKENS", {}) or {}).items() if v == tok), None)
        if r not in names:
            own =re.sub(r"\s*\(.*\)|\s*\d+$", "", nice.get(r, "")).replace("Late ", "").strip()
            if key == "u":
                names[r] = own or getattr(sys.modules["core"], "HERO", None) or "Hero"
                if isinstance(names[r], Dummy):
                    names[r] = "Hero"
                return names[r]
            base = KEYS.get(key) if key in KEYS else (own or "Tower")
            count[base] = count.get(base, 0) + 1
            names[r] = f"{base} {count[base]}"
        return names[r]
    tiers = {}
    rounds = []
    pre = list(getattr(D, "PRE", []) or [])
    steps = sorted((k, list(v)) for k, v in (I.STEPS or {}).items())
    if pre:
        steps = [(-1, pre)] + steps
    for rnd, ops in steps:
        lines = []
        for op in ops:
            kind = op[0]
            if kind == "place":
                key, pos = op[2]
                tiers[repr(pos)] = [0, 0, 0]
                lines.append([repr(pos), f"{name(pos, key)}", True])
            elif kind == "tier":
                pos, p, lvl = op[2]
                t = tiers.setdefault(repr(pos), [0, 0, 0])
                t[p] = max(t[p], lvl)
                tag = "-".join(map(str, t))
                if lines and lines[-1][0] == repr(pos) and not lines[-1][2] is None:
                    lines[-1][1] = re.sub(r" \d-\d-\d$", "", lines[-1][1]) + f" {tag}"
                else:
                    lines.append([repr(pos), f"{name(pos)} {tag}", False])
            elif kind == "target":
                pos, m = op[2]
                lines.append([repr(pos), f"{name(pos)} target {str(m).title()}", None])
            else:
                lines.append(["", op[3], None])
        rounds.append((rnd, [l[1] for l in lines]))
    for a in getattr(mod, "ABILITIES", []) or []:
        rnd, key = a[0], a[-1]
        rounds.append((rnd, [f"Ability {key}"]))
    merged = {}
    for rnd, ls in rounds:
        merged.setdefault(rnd, []).extend(ls)
    return [(r, merged[r]) for r in sorted(merged)]


# Scripts without the step machinery: their builds, as written in them (keep in step by hand)
HAND = {
    "dark_castle_deflation.py": [(-1, ["Dart 1 0-2-5"])],
    "flooded_easy.py": [(-1, ["Buccaneer 1 4-2-0", "Start round 1", "Sub 1 4-2-0", "Wizard 1 2-0-4"])],
    "ravine_deflation.py": [(-1, ["Village 1 0-2-1", "Buccaneer 1 4-2-0", "Start round 1", "Obyn", "Druid 1 0-3-0",
                                  "Druid 2 0-3-0", "Druid 3 0-3-0", "Boomerang 1 3-0-2"])],
    "sanctuary_deflation.py": [(-1, ["Village 1 0-2-1", "Buccaneer 1 4-2-0", "Obyn", "Wizard 1 2-0-4",
                                     "Druid 1 1-1-0", "Start round 1"])],
    "infernal_easy.py": [(-1, ["Start round 1", "Sniper 1 0-2-4", "Wizard 1 4-0-2", "Alchemist 1 2-0-0"])],
}


def main():
    # app list: script -> (map, mode); the same ENTRIES the app shows
    out = {}
    for f in sorted(os.listdir(os.path.join(HERE, "maps"))):
        if not f.endswith(".py"):
            continue
        if f in HAND:
            out[f] = [{"round": r, "steps": s} for r, s in HAND[f]]
            print(f"{f}: by hand")
            continue
        src = open(os.path.join(HERE, "maps", f), encoding="utf-8").read()
        if "STEPS" not in src:          # it would only show infernal_impop's build, left over
            print(f"{f}: skipped (no steps)")
            continue
        try:
            mod, I, D = load(f)
            if I is None or not getattr(I, "STEPS", None):
                raise ValueError("no steps")
            rows = describe(mod, I, D)
            out[f] = [{"round": r, "steps": s} for r, s in rows]
            print(f"{f}: {sum(len(s) for _, s in rows)} steps")
        except Exception as e:
            print(f"{f}: skipped ({type(e).__name__}: {e})")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
