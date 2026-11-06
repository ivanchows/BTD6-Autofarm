# /// script
# dependencies = ["mss", "pillow", "winrt-Windows.Media.Ocr", "winrt-Windows.Graphics.Imaging",
#                 "winrt-Windows.Storage.Streams", "winrt-Windows.Foundation",
#                 "winrt-Windows.Foundation.Collections", "winrt-Windows.Globalization"]
# ///
"""Reads every monkey's in-game costs off the Monkeys screen into tower_costs.json.

Open BTD6 on any monkey's upgrade screen (home > Monkeys > a monkey), then run
`uv run price_scan.py`. It clicks each upgrade and reads "Ingame cost"
(it never presses Buy), then the right arrow to the next monkey, until it is back where it
started. The screen shows Medium prices; core.cost() works out the other difficulties.
"""
import difflib
import json
import os
import re
import sys

import core as F

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tower_costs.json")
COLS = (623, 827, 1030, 1234, 1438)
ROWS = {"top": 330, "mid": 550, "bot": 765}
NEXT = (1480, 62)
NAME_BOX = (560, 10, 1000, 70)
COST_BOX = (200, 785, 500, 835)


KNOWN = ["Dart Monkey", "Boomerang Monkey", "Bomb Shooter", "Tack Shooter", "Ice Monkey",
         "Glue Gunner", "Desperado", "Sniper Monkey", "Monkey Sub", "Monkey Buccaneer", "Monkey Ace",
         "Heli Pilot", "Mortar Monkey", "Dartling Gunner", "Wizard Monkey", "Super Monkey",
         "Ninja Monkey", "Alchemist", "Druid", "Mermonkey", "Banana Farm", "Spike Factory",
         "Monkey Village", "Engineer Monkey", "Beast Handler", "Skywarden"]


def name(im):
    """The title, snapped to a known monkey (OCR reads "Dart Monxey", "Bomg Shooter")."""
    t = F._ocr(F.ImageOps.expand(im.crop(NAME_BOX).convert("L"), 30, fill=0)).strip()
    t = " ".join(w.capitalize() for w in t.split())
    m = difflib.get_close_matches(t, KNOWN, 1, 0.6)
    return m[0] if m else t


def cost():
    """The number after "Ingame cost", read until two reads agree."""
    last = None
    for _ in range(8):
        F.wait(0.25)
        c = F.grab().crop(COST_BOX)
        for v in F._gray(c):
            t = F._ocr(v).replace(" ", "").replace(".", ",")
            m = re.search(r"(\d{1,3}(?:,\d{3})+|\d+)\s*$", t)
            if m:
                n = int(m.group(1).replace(",", ""))
                if n == last:
                    return n
                last = n
                break
    return last


def main():
    F.focus()
    F.wait(0.5)
    try:
        data = {k: v for k, v in json.load(open(OUT, encoding="utf-8")).items() if k in KNOWN}
    except Exception:
        data = {}
    first = None
    seen = set()
    one = sys.argv[1] if len(sys.argv) > 1 else None    # price_scan.py "Sniper Monkey": this screen only
    for _ in range(40):
        nm = one or name(F.grab())
        if nm == first:
            break
        if nm in seen:      # a misread title ("Sniper" read as "Super") overwrites another monkey
            print(f"read {nm} twice (misread title?): rescan it with price_scan.py \"<name>\"")
        seen.add(nm)
        first = first or nm
        row = dict(data.get(nm, {}))
        for path, y in ROWS.items():
            row[path] = []
            for x in COLS:
                F.click(x, y)
                row[path].append(cost())
        print(nm, row, flush=True)
        data[nm] = row
        json.dump({"_note": "Medium prices: top/mid/bot = each path's tier 1-5 upgrade, read off the Monkeys screen (Ingame cost). core.cost() scales them per difficulty.", **data},
                  open(OUT, "w", encoding="utf-8", newline="\n"), indent=1)
        if one:
            break
        F.click(*NEXT)
        F.wait(1.0)
    print(f"saved {len(data)} monkeys to {OUT}")


if __name__ == "__main__":
    main()
