# /// script
# dependencies = ["pillow"]
# ///
"""BTD6 Autofarm app: pick a map (or the bonus map), Start / Pause / Stop, AFK mode,
live stats and the farm's log. Open it with Autofarm.bat.

Drawn smooth, in BTD6's menu blue: white-rimmed buttons with a soft gradient face, soft
shadows, a clean rounded font (Fredoka, assets/). Everything is rendered with Pillow at 3x and
shown on one Tk canvas.

It runs watchdog.py like Play.bat does. Buttons reach the running farm through gui_cmd.txt
(core.gui_command), so they also work on a farm started from Play.bat."""
import ctypes
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

OPENED = time.time()        # when this copy of the app was loaded

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "state.json")
FARM_LOG = os.path.join(HERE, "farm.log")
WATCH_LOG = os.path.join(HERE, "watchdog.log")
CMD_FILE = os.path.join(HERE, "gui_cmd.txt")
PREFS = os.path.join(HERE, "gui.json")
SKIP_FILE = os.path.join(HERE, "skipped_maps.json")
BONUS_FILE = os.path.join(HERE, "bonus_map.txt")
FONT_FILE = os.path.join(HERE, "assets", "Fredoka.ttf")
NO_WINDOW = 0x08000000
STEAM_URL = "steam://rungameid/960090"      # Bloons TD 6 (the same link core.relaunch uses)
GAME_LOAD = 25                              # seconds after the window shows before the farm starts
W, H = 1120, 740

BONUS_PLAYS = {  # map -> the farm bonus mode plays there (watchdog.BONUS_SCRIPTS)
    "Infernal": "infernal_impop.py", "Flooded Valley": "flooded_valley_impop.py@easy",
    "Sanctuary": "sanctuary_deflation.py", "Ravine": "ravine_deflation.py",     # Sanctuary: Deflation (user)
    "Quad": "quad_easy.py", "Workshop": "workshop_easy.py", "Dark Dungeons": "dark_dungeons_easy.py",
    "Bloody Puddles": "bloody_puddles_easy.py", "Tricky Tracks": "tricky_tracks_easy.py",
    "#Ouch": "ouch_easy.py", "Dark Castle": "dark_castle_impop.py",
    "Muddy Puddles": "muddy_puddles_impop.py", "Glacial Trail": "glacial_trail_impop.py",
}
MAPS = [  # file, map, mode, hero (Infernal is Impoppable only: user, 2026-11-05)
    ("flooded_easy.py", "Flooded Valley", "Deflation", None),
    ("sanctuary_deflation.py", "Sanctuary", "Deflation", "Obyn"),
    ("ravine_deflation.py", "Ravine", "Deflation", "Obyn"),
    ("infernal_easy.py", "Infernal", "Deflation", None),
    ("dark_castle_deflation.py", "Dark Castle", "Deflation", None),
    ("quad_easy.py", "Quad", "Easy", "Etienne"),
    ("workshop_easy.py", "Workshop", "Easy", "Sauda"),
    ("dark_dungeons_easy.py", "Dark Dungeons", "Easy", "Obyn"),
    ("bloody_puddles_easy.py", "Bloody Puddles", "Easy", None),
    ("tricky_tracks_easy.py", "Tricky Tracks", "Easy", "Quincy"),
    ("ouch_easy.py", "#Ouch", "Easy", None),
    ("infernal_impop.py", "Infernal", "Impoppable", "Benjamin"),
    ("flooded_valley_impop.py", "Flooded Valley", "Impoppable", "Etienne"),
    ("dark_castle_impop.py", "Dark Castle", "Impoppable", "Striker Jones"),
    ("muddy_puddles_impop.py", "Muddy Puddles", "Impoppable", "Psi"),
    ("glacial_trail_impop.py", "Glacial Trail", "Impoppable", "Silas"),
    ("sanctuary_impop.py", "Sanctuary", "Impoppable", "Obyn"),
]

# One soft blue palette. Buttons keep BTD6's white rim (thinner) over a smooth two-tone face;
# the lettering has a thin outline in the button's own dark shade and a blurred shadow.
GREEN = {"face": ("#86e463", "#41bd3e", "#289d2f"), "border": "#1d8028", "ink": "#135a1b"}
YELLOW = {"face": ("#ffe47a", "#ffc531", "#f69c14"), "border": "#d9840b", "ink": "#7f4500"}
RED = {"face": ("#ff958b", "#f2554f", "#d3333e"), "border": "#ae2230", "ink": "#6b0f19"}
BLUE = {"face": ("#99d6ff", "#4aa8f6", "#2b80e1"), "border": "#1f64be", "ink": "#0e3c7c"}
GREY = {"face": ("#e3e8ef", "#b8c2cf", "#95a1b2"), "border": "#77839a", "ink": "#3b4455"}
MODE_COLOR = {"Deflation": "#56c6ff", "Easy": "#6be08a", "Medium": "#ffd84a", "Hard": "#ff9a45",
              "Impoppable": "#ff6f7d"}
COLS = [("Deflation", "DEFL"), ("Easy", "EASY"), ("Medium", "MED"), ("Hard", "HARD"), ("Impoppable", "IMPOP")]
# key (what the watchdog is given) -> (map, mode). An Impoppable build also plays Easy / Medium / Hard
# Standard: "<file>@easy" etc. (user, 2026-11-07)
# A build not proven on every difficulty yet: only these (user, 2026-11-08)
ONLY = {"flooded_valley_impop.py": ("Easy", "Medium")}
ENTRIES = {}
for _f, _m, _mode, _h in MAPS:
    if _mode in ONLY.get(_f, (_mode,)):
        ENTRIES[_f] = (_m, _mode)
    if _mode == "Impoppable":
        for _d in ONLY.get(_f, ("Easy", "Medium", "Hard")):
            if not any(m == _m and md == _d for m, md in ENTRIES.values()):
                ENTRIES[f"{_f}@{_d.lower()}"] = (_m, _d)
ROWS = sorted({m for m, _ in ENTRIES.values()}, key=lambda m: m.lstrip("#").lower())
TILE = {"face": ("#3274d6", "#2964c4", "#2155ae"), "border": "#17418c", "ink": "#0b2858"}
TILE_LOCKED = {"face": ("#6b7891", "#5a6680", "#4c5770"), "border": "#3b4458", "ink": "#232a38"}
INK = "#0b2350"          # deep navy outline
GOLD = "#ffd35a"
CREAM = "#d4e4ff"        # soft blue-white for small labels
WELL = "#123374"         # the sunken boxes (stats, now playing, log)


# ---------------------------------------------------------------- drawing
# Everything is drawn at SS times its size and shrunk with Lanczos: smooth, anti-aliased edges.
SS = 3
_fonts = {}


def font(size):
    if size not in _fonts:
        try:
            f = ImageFont.truetype(FONT_FILE, size)
            try:
                f.set_variation_by_name("SemiBold")
            except Exception:
                pass
        except OSError:
            f = ImageFont.truetype("segoeuib.ttf", size)
        _fonts[size] = f
    return _fonts[size]


def rgb(c):
    if isinstance(c, tuple):
        return c[:3]
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(rgb(a), rgb(b)))


def gradient(w, h, stops):
    """A vertical gradient through 2 or 3 colours."""
    g = Image.new("RGBA", (1, h))
    n = len(stops) - 1
    for y in range(h):
        t = y / max(1, h - 1) * n
        i = min(int(t), n - 1)
        g.putpixel((0, y), mix(stops[i], stops[i + 1], t - i) + (255,))
    return g.resize((w, h))


def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    return m


def down(im, w=None, h=None):
    return im.resize((w or round(im.width / SS), h or round(im.height / SS)), Image.LANCZOS)


def soft_shadow(src, blur, alpha, dy):
    """A blurred drop shadow from an image's alpha, moved down dy."""
    a = src.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", src.size, (0, 0, 0, 0))
    sh.putalpha(a)
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, dy))
    return out


def text_img(text, size, fill="white", stroke=INK, sw=None, shadow=True, max_w=None, angle=0, grad=None):
    """Clean rounded lettering: a thin outline and a soft shadow (no heavy cartoon ink)."""
    while True:
        sw_ = sw if sw is not None else max(1, round(size / 15))
        f = font(size * SS)
        x0, y0, x1, y1 = f.getbbox(text, stroke_width=sw_ * SS)
        if max_w is None or (x1 - x0) / SS <= max_w or size <= 10:
            break
        size -= 1
    k = SS
    pad = 4 * k
    im = Image.new("RGBA", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad + 2 * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    at = (pad - x0, pad - y0)
    if sw_:
        d.text(at, text, font=f, fill=stroke, stroke_width=sw_ * k, stroke_fill=stroke)
    if grad:
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).text(at, text, font=f, fill=255)
        im.paste(gradient(im.width, im.height, grad), (0, 0), mask)
    else:
        d.text(at, text, font=f, fill=fill)
    if shadow:
        base = Image.new("RGBA", im.size, (0, 0, 0, 0))
        base.alpha_composite(soft_shadow(im, 2 * k, 120, max(1, size // 16) * k))
        base.alpha_composite(im)
        im = base
    if angle:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    return down(im)


def btd_button(w, h, style, r=None, rim=3, glow=False):
    """BTD6's button, smoothed: a soft shadow, a thin white rim, a fine border of its own
    colour, a smooth three-stop face and a faint gloss on top."""
    k = SS
    W_, H_ = w * k, h * k
    r_ = (r if r is not None else min(w, h) * 0.32) * k
    m = 6 * k
    body = Image.new("RGBA", (W_ + 2 * m, H_ + 2 * m), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle((m, m, m + W_ - 1, m + H_ - 1), r_, fill="#ffffff")
    b = rim * k
    d.rounded_rectangle((m + b, m + b, m + W_ - 1 - b, m + H_ - 1 - b), r_ - b, fill=style["border"])
    i = b + k
    fw, fh = W_ - 2 * i, H_ - 2 * i
    face = gradient(fw, fh, style["face"])
    gloss = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).rounded_rectangle((3 * k, 2 * k, fw - 3 * k, int(fh * 0.45)), max(2 * k, r_ - i - 2 * k),
                                            fill=(255, 255, 255, 45))
    face.alpha_composite(gloss)
    body.paste(face, (m + i, m + i), rounded_mask(fw, fh, max(1, r_ - i)))
    im = soft_shadow(body, 5 * k, 110, 3 * k)
    im.alpha_composite(body)
    return down(im)


def tile(w, h, style, mode_color=None, glow=False):
    """A map card: smooth navy face, a fine border, and a slim stripe in the mode's colour."""
    k = SS
    W_, H_ = w * k, h * k
    r_ = 12 * k
    m = 6 * k
    body = Image.new("RGBA", (W_ + 2 * m, H_ + 2 * m), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    if glow:
        d.rounded_rectangle((m - 3 * k, m - 3 * k, m + W_ - 1 + 3 * k, m + H_ - 1 + 3 * k), r_ + 3 * k,
                            fill=GOLD)
    d.rounded_rectangle((m, m, m + W_ - 1, m + H_ - 1), r_, fill=style["border"])
    i = 2 * k
    fw, fh = W_ - 2 * i, H_ - 2 * i
    face = gradient(fw, fh, style["face"])
    fd = ImageDraw.Draw(face)
    fd.line([(r_, 1 * k), (fw - r_, 1 * k)], fill=mix(style["face"][0], "#ffffff", 0.35) + (255,), width=k)
    if mode_color:
        fd.rectangle((0, 0, 6 * k, fh), fill=mode_color)
    body.paste(face, (m + i, m + i), rounded_mask(fw, fh, r_ - i))
    im = soft_shadow(body, 4 * k, 90, 2 * k)
    im.alpha_composite(body)
    return down(im)


def panel(w, h, seed=None):
    """A soft raised panel: lighter blue, a fine light edge, a blurred shadow underneath."""
    k = 2
    m = 12 * k
    W_, H_ = w * k, h * k
    r_ = 18 * k
    body = Image.new("RGBA", (W_ + 2 * m, H_ + 2 * m), (0, 0, 0, 0))
    d = ImageDraw.Draw(body)
    d.rounded_rectangle((m, m, m + W_ - 1, m + H_ - 1), r_, fill=(126, 178, 255, 150))
    iw, ih = W_ - 2 * k, H_ - 2 * k
    face = gradient(iw, ih, ("#3474d8", "#2a62c2", "#2353ab"))
    face.putalpha(222)                      # a little see-through: the background's glow shows
    body.paste(face, (m + k, m + k), rounded_mask(iw, ih, r_ - k))
    im = soft_shadow(body, 10 * k, 110, 5 * k)
    im.alpha_composite(body)
    im = im.resize((round(im.width / k), round(im.height / k)), Image.LANCZOS)
    return im      # 12 px of shadow margin on every side


def plate(w, h, fill=WELL, c=None):
    """A sunken box inside a panel: darker, with a soft inner shadow along its top."""
    k = SS
    W_, H_, r_ = w * k, h * k, 12 * k
    im = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    im.paste(gradient(W_, H_, (mix(fill, "#000000", 0.12), fill)), (0, 0), rounded_mask(W_, H_, r_))
    sh = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((0, 0, W_ - 1, H_ - 1), r_, outline=(0, 0, 0, 120), width=4 * k)
    sh = sh.filter(ImageFilter.GaussianBlur(3 * k))
    mask = rounded_mask(W_, H_, r_)
    clip = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    clip.paste(sh, (0, 0), mask)
    im.alpha_composite(clip)
    ImageDraw.Draw(im).rounded_rectangle((0, 0, W_ - 1, H_ - 1), r_, outline=(150, 190, 255, 60), width=k)
    return down(im, w, h)


def ghost_bloon(size, alpha):
    """A frosted bloon silhouette for the background: soft white, no outline."""
    k = SS
    sz = size * k
    im = Image.new("RGBA", (sz, int(sz * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((sz * .08, 0, sz * .92, sz * 1.04), fill=(255, 255, 255, alpha))
    d.polygon([(sz * .42, sz * 1.1), (sz * .58, sz * 1.1), (sz * .5, sz * 1.0)], fill=(255, 255, 255, alpha))
    d.line([(sz * .5 + math.sin(t / 3) * sz * .06, sz * 1.1 + t * sz * .022) for t in range(20)],
           fill=(255, 255, 255, alpha // 2), width=max(2, sz // 40), joint="curve")
    d.ellipse((sz * .26, sz * .16, sz * .40, sz * .36), fill=(255, 255, 255, min(255, alpha * 2)))
    return down(im).filter(ImageFilter.GaussianBlur(0.6))


GHOSTS = [  # (x, y, size, alpha): mostly in the title bar, a few behind the see-through panels
    (640, 6, 40, 70), (712, 22, 30, 55), (770, 2, 36, 65), (838, 18, 28, 50), (888, 4, 34, 60),
    (150, 520, 120, 26), (900, 560, 140, 22), (560, 150, 90, 24),
]


def background():
    """Menu blue with depth: soft cyan and violet glows, a hex pattern that fades out toward the
    bottom, a dark vignette, and frosted bloons drifting at the top."""
    w, h = W, H
    bg = gradient(w, h, ("#1f63cc", "#17449e", "#0c2766"))
    q = 8                                   # glows drawn small, blurred, scaled up: soft and fast
    glow = Image.new("RGBA", (w // q, h // q), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((-0.25 * w / q, -0.6 * h / q, 0.55 * w / q, 0.55 * h / q), fill=(80, 205, 255, 130))
    g.ellipse((0.55 * w / q, 0.45 * h / q, 1.3 * w / q, 1.5 * h / q), fill=(125, 85, 255, 95))
    g.ellipse((0.35 * w / q, -0.35 * h / q, 0.95 * w / q, 0.28 * h / q), fill=(170, 220, 255, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(14)).resize((w, h), Image.BICUBIC)
    bg.alpha_composite(glow)

    k = 2
    hexes = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(hexes)
    sz = 34 * k
    for row in range(-1, int(h * k / (sz * 1.5)) + 2):
        for col in range(-1, int(w * k / (sz * math.sqrt(3))) + 2):
            cx = col * sz * math.sqrt(3) + (row % 2) * sz * math.sqrt(3) / 2
            cy = row * sz * 1.5
            pts = [(cx + sz * math.cos(math.radians(60 * j + 30)), cy + sz * math.sin(math.radians(60 * j + 30)))
                   for j in range(6)]
            d.polygon(pts, outline=(255, 255, 255, 255), width=2 * k)
    hexes = hexes.resize((w, h), Image.LANCZOS)
    fade = gradient(1, h, ("#ffffff", "#5a5a5a", "#000000")).convert("L").resize((w, h))
    hexes.putalpha(Image.eval(Image.composite(hexes.split()[3], Image.new("L", (w, h), 0), fade),
                              lambda v: v * 22 // 255))
    bg.alpha_composite(hexes)

    vig = Image.new("L", (w // q, h // q), 0)
    ImageDraw.Draw(vig).ellipse((-0.15 * w / q, -0.2 * h / q, 1.15 * w / q, 1.2 * h / q), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(10)).resize((w, h), Image.BICUBIC)
    dark = Image.new("RGBA", (w, h), (4, 12, 40, 0))
    dark.putalpha(Image.eval(vig, lambda v: (255 - v) * 150 // 255))
    bg.alpha_composite(dark)

    for x, y, size, alpha in GHOSTS:
        bg.alpha_composite(ghost_bloon(size, alpha), (x, y))
    return bg


def icon(kind, size=40):
    """Small smooth icons: flat colour, a fine dark edge, a highlight."""
    k = SS
    s = size * k
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = max(2, int(s * 0.05))
    edge = INK
    if kind == "wins":          # a gold trophy
        d.arc((s * .04, s * .14, s * .36, s * .46), 90, 270, fill=GOLD, width=w * 2)
        d.arc((s * .64, s * .14, s * .96, s * .46), 270, 90, fill=GOLD, width=w * 2)
        d.rounded_rectangle((s * .2, s * .06, s * .8, s * .56), s * .2, fill=GOLD, outline=edge, width=w)
        d.rectangle((s * .43, s * .54, s * .57, s * .74), fill="#e9ac16")
        d.rounded_rectangle((s * .26, s * .72, s * .74, s * .92), s * .05, fill=GOLD, outline=edge, width=w)
        d.ellipse((s * .3, s * .13, s * .4, s * .28), fill=(255, 255, 255, 170))
    elif kind == "losses":      # a heart
        c = "#ff5a64"
        d.ellipse((s * .08, s * .14, s * .52, s * .58), fill=c)
        d.ellipse((s * .48, s * .14, s * .92, s * .58), fill=c)
        d.polygon([(s * .1, s * .44), (s * .9, s * .44), (s * .5, s * .92)], fill=c)
        d.ellipse((s * .2, s * .22, s * .32, s * .34), fill=(255, 255, 255, 170))
    elif kind == "candy":       # a wrapped sweet
        d.polygon([(s * .04, s * .24), (s * .32, s * .5), (s * .04, s * .76)], fill="#ff9fd8")
        d.polygon([(s * .96, s * .24), (s * .68, s * .5), (s * .96, s * .76)], fill="#ff9fd8")
        d.ellipse((s * .22, s * .22, s * .78, s * .78), fill="#ff4fa6")
        d.ellipse((s * .33, s * .3, s * .45, s * .42), fill=(255, 255, 255, 180))
    elif kind == "time":        # a clock
        d.ellipse((s * .08, s * .08, s * .92, s * .92), fill="#ffffff")
        d.line([(s * .5, s * .5), (s * .5, s * .24)], fill=INK, width=w)
        d.line([(s * .5, s * .5), (s * .69, s * .6)], fill="#ff5a64", width=w)
        d.ellipse((s * .45, s * .45, s * .55, s * .55), fill=INK)
    return down(im, size, size)


def star(size, fill=GOLD):
    k = SS
    s = size * k
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    c, R, r = s / 2, s / 2 - 2 * k, s / 4.3
    pts = [(c + (R if j % 2 == 0 else r) * math.cos(math.radians(-90 + 36 * j)),
            c + (R if j % 2 == 0 else r) * math.sin(math.radians(-90 + 36 * j))) for j in range(10)]
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=fill, outline=mix(fill, "#7a4a00", 0.6), width=max(2, s // 20))
    return down(im, size, size)


def chip(text, color, size=13):
    """A small rounded label (mode, PLAYING, LOCKED)."""
    t = text_img(text, size, sw=0, shadow=False)
    k = SS
    w, h = t.width + 12, t.height + 2
    im = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w * k - 1, h * k - 1), h * k // 2, fill=color)
    im = down(im, w, h)
    im.alpha_composite(t, (6, 1))
    return im


def compose(base, *layers):
    """Paste (image, (x, y) or 'center') layers onto a copy of base."""
    im = base.copy()
    for layer, at in layers:
        if at == "center":
            at = ((im.width - layer.width) // 2, (im.height - layer.height) // 2)
        im.alpha_composite(layer, (int(at[0]), int(at[1])))
    return im


# ---------------------------------------------------------------- helpers
def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def tail(path, n):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 16000))
            return f.read().decode("utf-8", "replace").splitlines()[-n:]
    except OSError:
        return []


def find_uv():
    for p in (shutil.which("uv"), os.path.expanduser(r"~\.local\bin\uv.exe"),
              os.path.expanduser(r"~\.cargo\bin\uv.exe"),
              os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe")):
        if p and os.path.exists(p):
            return p
    return None


def game_open():
    """Is BTD6 running? Its window is titled BloonsTD6."""
    try:
        return bool(ctypes.windll.user32.FindWindowW(None, "BloonsTD6"))
    except Exception:
        return False


def hms(sec):
    sec = int(max(0, sec))
    return f"{sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}"


# ---------------------------------------------------------------- canvas widgets
class Sprite:
    """An image on the canvas that is redrawn only when its key changes."""

    def __init__(self, cv, x, y, anchor="nw"):
        self.cv, self.key, self.photo = cv, None, None
        self.id = cv.create_image(x, y, anchor=anchor)

    def show(self, key, make):
        if key != self.key:
            self.key = key
            self.photo = ImageTk.PhotoImage(make())
            self.cv.itemconfigure(self.id, image=self.photo)


class Button:
    """A BTD6 button: brightens on hover, sinks 2 px while pressed."""
    PAD = 6

    def __init__(self, app, x, y, w, h, on_click, size=26, r=None):
        self.app, self.x, self.y, self.w, self.h = app, x, y, w, h
        self.size, self.r, self.on_click = size, r, on_click
        self.label, self.style, self.enabled = "", GREEN, True
        self.hover = self.down = False
        self.sprite = Sprite(app.cv, x - self.PAD, y - self.PAD)
        cv = app.cv
        cv.tag_bind(self.sprite.id, "<Enter>", lambda e: self._set(hover=True))
        cv.tag_bind(self.sprite.id, "<Leave>", lambda e: self._set(hover=False, down=False))
        cv.tag_bind(self.sprite.id, "<ButtonPress-1>", lambda e: self._set(down=True))
        cv.tag_bind(self.sprite.id, "<ButtonRelease-1>", self._release)

    def _set(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self.app.cv.configure(cursor="hand2" if self.hover and self.enabled else "")
        self.draw()

    def _release(self, _):
        was = self.down
        self._set(down=False)
        if was and self.hover and self.enabled:
            self.on_click()

    def set(self, label=None, style=None, enabled=None):
        if label is not None:
            self.label = label
        if style is not None:
            self.style = style
        if enabled is not None:
            self.enabled = enabled
        self.draw()

    def look(self):
        st = self.style if self.enabled else GREY
        if self.hover and self.enabled and not self.down:
            st = dict(st, face=tuple(mix(c, "#ffffff", 0.15) for c in st["face"]))
        return st

    def base(self, st):
        return btd_button(self.w, self.h, st, r=self.r)

    def layers(self, st):
        if not self.label:
            return []
        t = text_img(self.label, self.size, stroke=st["ink"], max_w=self.w - 24)
        return [(t, "center")]

    def draw(self):
        st = self.look()
        press = 2 if self.down and self.enabled else 0
        key = (self.label, repr(st), press, self.extra_key())

        def make():
            b = compose(self.base(st), *self.layers(st))
            out = Image.new("RGBA", (b.width, b.height + 2), (0, 0, 0, 0))
            out.alpha_composite(b, (0, press))
            return out
        self.sprite.show(key, make)

    def extra_key(self):
        return None


class MapCell(Button):
    """One mode of one map: blue with the mode's colour as its label; yellow = picked, green = playing."""

    def __init__(self, app, x, y, w, h, key, mode, label):
        self.key, self.mode, self.text = key, mode, label
        self.state = (False, False, False)
        super().__init__(app, x, y, w, h, lambda: app.pick(key), size=13, r=10)
        self.draw()

    def set_state(self, chosen, playing, locked):
        st = (chosen, playing, locked)
        if st != self.state:
            self.state = st
            self.draw()

    def extra_key(self):
        return self.state

    def look(self):
        chosen, playing, locked = self.state
        st = GREEN if playing else YELLOW if chosen else TILE_LOCKED if locked else TILE
        if self.hover and not self.down:
            st = dict(st, face=tuple(mix(c, "#ffffff", 0.15) for c in st["face"]))
        return st

    def base(self, st):
        return btd_button(self.w, self.h, st, r=self.r, rim=2)

    def layers(self, st):
        chosen, playing, locked = self.state
        fill = "white" if (chosen or playing) else CREAM if locked else MODE_COLOR[self.mode]
        return [(text_img(self.text, self.size, fill=fill, stroke=st["ink"], max_w=self.w - 8), "center")]


# ---------------------------------------------------------------- app
class App:
    def __init__(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        self.root = tk.Tk()
        self.root.title("BTD6 Autofarm")
        self.root.resizable(False, False)
        self.root.geometry(f"{W}x{H}")
        self.root.configure(bg="#163f95")
        self.icon = ImageTk.PhotoImage(star(64))
        self.root.iconphoto(True, self.icon)
        self.cv = tk.Canvas(self.root, width=W, height=H, highlightthickness=0, bd=0, bg="#163f95")
        self.cv.pack()
        self.prefs = read_json(PREFS, {"mode": "bonus", "map": "muddy_puddles_impop.py", "afk": False})
        if self.prefs.get("mode") not in ("bonus", "map"):
            self.prefs["mode"] = "bonus"
        if self.prefs.get("map") not in ENTRIES:
            self.prefs["map"] = "infernal_impop.py"
        self.proc = None
        self.stop_at = None
        self.updating = False
        self.restart_ready = False
        self.update_ready = False           # a newer version is on GitHub: the button says UPDATE
        self.keep = []
        self.build()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh()
        self.root.after(1500, self.check_update)    # on open: update by itself
        self.root.after(self.CHECK_EVERY, self.check_often)

    def static(self, img, x, y, anchor="nw"):
        p = ImageTk.PhotoImage(img)
        self.keep.append(p)
        return self.cv.create_image(x, y, image=p, anchor=anchor)

    def build(self):
        cv = self.cv
        self.static(background(), 0, 0)
        t = text_img("BTD6", 44, grad=("#ffe98a", "#ffc93a", "#ffa21a"), stroke="#7a4300", sw=2)
        self.static(t, 18, 14)
        t2 = text_img("AUTOFARM", 44, sw=2)
        self.static(t2, 22 + t.width, 14)
        self.pill = Sprite(cv, 22 + t.width + t2.width + 14, 20)
        self.game_btn = Button(self, 22 + t.width + t2.width + 182, 26, 168, 42, self.open_game, size=17, r=21)
        self.waiting_since = None       # Start pressed with the game closed: when it was opened
        self.update_btn = Button(self, W - 216, 20, 196, 52, self.do_update, size=22)
        self.update_btn.set("CHECK UPDATE", BLUE)

        # left: the maps, on wood like the in-game tower shop
        LX, LY, LW, LH = 16, 92, 462, H - 108
        self.static(panel(LW, LH), LX - 12, LY - 12)
        # EVENT MODE (the Collection Event's bonus map) on/off; picking a map below turns it off
        self.bonus_btn = Button(self, LX + 22, LY + 20, LW - 44, 54,
                                lambda: self.set_mode("map" if self.prefs["mode"] == "bonus" else "bonus"), size=24)
        self.cells, self.row_names = {}, {}
        cw, gap, rh, pitch = 50, 5, 34, 40
        cx0 = LX + LW - 22 - 5 * cw - 4 * gap
        for i, name in enumerate(ROWS):
            y = LY + 94 + i * pitch
            self.static(plate(LW - 44, rh + 2, fill="#16408c"), LX + 22, y - 1)
            self.row_names[name] = Sprite(cv, LX + 34, y + rh // 2, anchor="w")
            for j, (mode, label) in enumerate(COLS):
                key = next((k for k, v in ENTRIES.items() if v == (name, mode)), None)
                if key:
                    self.cells[key] = MapCell(self, cx0 + j * (cw + gap), y + 3, cw, rh - 6, key, mode, label)

        # right: one wood board with the stats, what's playing, the controls and the log
        RX, RY, RW, RH = 494, 92, W - 494 - 16, H - 108
        self.static(panel(RW, RH), RX - 12, RY - 12)
        cw = (RW - 44 - 3 * 10) // 4
        self.stats = {}
        for i, k in enumerate(("wins", "losses", "candy", "time")):
            x = RX + 22 + i * (cw + 10)
            self.static(plate(cw, 96), x, RY + 20)
            self.static(icon(k, 34), x + 10, RY + 30)
            self.static(text_img(k.upper(), 14, fill=CREAM, sw=0, shadow=False), x + 50, RY + 38)
            self.stats[k] = Sprite(cv, x + cw // 2, RY + 92, anchor="center")

        self.static(plate(RW - 44, 116), RX + 22, RY + 128)
        self.now_map = Sprite(cv, RX + 40, RY + 140)
        self.now_status = Sprite(cv, RX + 42, RY + 186)
        self.now_next = Sprite(cv, RX + 42, RY + 210)

        cy = RY + 262
        self.start_btn = Button(self, RX + 22, cy, 250, 76, self.on_start, size=38)
        self.pause_btn = Button(self, RX + 288, cy, 160, 76, self.on_pause, size=28)
        self.afk_btn = Button(self, RX + 464, cy, RW - 486, 76, self.on_afk, size=24)

        ly = cy + 100
        lh = RY + RH - ly - 70
        self.static(plate(RW - 44, lh, fill="#0f2c66"), RX + 22, ly)
        sty = ttk.Style(self.root)
        sty.theme_use("clam")
        sty.layout("Log.Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        sty.configure("Log.Vertical.TScrollbar", troughcolor="#0f2c66", background="#3f7fe0", bordercolor="#0f2c66",
                      lightcolor="#3f7fe0", darkcolor="#3f7fe0", gripcount=0, arrowsize=10, relief="flat")
        sty.map("Log.Vertical.TScrollbar", background=[("active", "#6aa6ff"), ("pressed", "#8cbcff")],
                lightcolor=[("active", "#6aa6ff")], darkcolor=[("active", "#6aa6ff")])
        self.log = tk.Text(self.root, bg="#0f2c66", fg=CREAM, bd=0, highlightthickness=0,
                           font=("Consolas", 10), wrap="none", relief="flat", cursor="arrow",
                           insertwidth=0, selectbackground="#3f7fe0", selectforeground="white", padx=2)
        self.log_bar = ttk.Scrollbar(self.root, orient="vertical", style="Log.Vertical.TScrollbar",
                                     command=self.log.yview)
        self.log.configure(yscrollcommand=self.on_log_scroll)
        cv.create_window(RX + 38, ly + 14, window=self.log, anchor="nw", width=RW - 96, height=lh - 26)
        cv.create_window(RX + RW - 52, ly + 12, window=self.log_bar, anchor="nw", width=10, height=lh - 24)
        for tag, color in (("err", "#ff8f8f"), ("good", "#8cf29a"), ("info", "#ffd35a"), ("dim", "#7f9bd0")):
            self.log.tag_configure(tag, foreground=color)
        self.log.configure(state="disabled")
        self.log.bind("<Control-c>", lambda e: self.log.event_generate("<<Copy>>"))
        self.latest_btn = Button(self, RX + RW - 160, ly + lh - 50, 96, 34, self.jump_latest, size=13, r=12)
        self.latest_btn.set("LATEST", BLUE)
        cv.itemconfigure(self.latest_btn.sprite.id, state="hidden")
        self.log_pos = 0            # bytes of farm.log already shown
        self.log_rest = ""          # a line the farm hasn't finished writing yet
        self.log_follow = True      # stick to the newest line until the user scrolls up
        self.read_log()

        # keybinds: click one, press a key; saved to settings.json (the farm reads it at start)
        self.listening = None
        cl = 96                                 # CLEAR (the log box only; farm.log is kept)
        kw = (RW - 44 - cl - 3 * 12) // 3
        self.key_btns = {}
        for i, name in enumerate(("pause", "stop", "afk")):
            self.key_btns[name] = Button(self, RX + 22 + i * (kw + 12), RY + RH - 58, kw, 40,
                                         lambda n=name: self.listen(n), size=15, r=14)
        self.clear_btn = Button(self, RX + RW - 22 - cl, RY + RH - 58, cl, 40, self.clear_log, size=15, r=14)
        self.clear_btn.set("CLEAR", BLUE)
        self.root.bind("<KeyPress>", self.on_key)
        self.paint_keys()
        self.paint_mode()

    # ---------------------------------------------------------------- keybinds
    KEY_DEFAULT = {"pause": "Numpad1", "stop": "Numpad0", "afk": "Numpad2"}
    # Tk's key names -> the names settings.json (keys.py) takes. Only keys BTD6 doesn't use:
    # letters, digits and , . / are tower and upgrade hotkeys in the game.
    TK_KEYS = {**{f"KP_{i}": f"Numpad{i}" for i in range(10)}, **{f"F{i}": f"F{i}" for i in range(1, 25)},
               "KP_Insert": "Insert", "KP_End": "End", "KP_Home": "Home", "KP_Prior": "PageUp",
               "KP_Next": "PageDown", "KP_Delete": "Delete", "KP_Up": "Up", "KP_Down": "Down",
               "KP_Left": "Left", "KP_Right": "Right", "Insert": "Insert", "Delete": "Delete",
               "Home": "Home", "End": "End", "Prior": "PageUp", "Next": "PageDown", "Pause": "Pause",
               "Scroll_Lock": "ScrollLock", "Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right"}

    def keys(self):
        return {**self.KEY_DEFAULT, **{k: v for k, v in read_json(os.path.join(HERE, "settings.json"), {}).items()
                                      if k in self.KEY_DEFAULT and isinstance(v, str)}}

    def paint_keys(self):
        keys = self.keys()
        for name, b in self.key_btns.items():
            if self.listening == name:
                b.set("PRESS A KEY", YELLOW)
            else:
                b.set(f"{name.upper()}  ·  {keys[name].upper()}", BLUE)

    def listen(self, name):
        self.listening = None if self.listening == name else name
        self.paint_keys()

    def on_key(self, e):
        name = self.listening
        if not name:
            return
        self.listening = None
        if e.keysym == "Escape":
            return self.paint_keys()
        key = self.TK_KEYS.get(e.keysym)
        if not key:
            self.paint_keys()
            return self.toast("Pick a key BTD6 doesn't use: F-keys, numpad, Home, End...")
        keys = self.keys()
        clash = next((n for n, v in keys.items() if n != name and v.upper() == key.upper()), None)
        if clash:
            self.paint_keys()
            return self.toast(f"{key} is already {clash.upper()}.")
        path = os.path.join(HERE, "settings.json")
        data = read_json(path, {})
        data[name] = key
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            return self.toast("Couldn't save settings.json.")
        self.paint_keys()
        self.toast(f"{name.upper()} is {key} now." + (" It works from the next start." if self.running() else ""))

    # ---------------------------------------------------------------- actions
    def save_prefs(self):
        try:
            with open(PREFS, "w", encoding="utf-8") as f:
                json.dump(self.prefs, f)
        except OSError:
            pass

    def set_mode(self, m):
        if self.running():
            return
        self.prefs["mode"] = m
        self.save_prefs()
        self.paint_mode()
        self.refresh_tiles()

    def paint_mode(self):
        bonus = self.prefs["mode"] == "bonus"
        self.bonus_btn.set("EVENT MODE", YELLOW if bonus else BLUE)

    def pick(self, fn):
        if self.running():
            return
        self.prefs.update(map=fn, mode="map")
        self.save_prefs()
        self.paint_mode()
        self.refresh_tiles()

    def send(self, word):
        with open(CMD_FILE, "w", encoding="utf-8") as f:
            f.write(word)

    def on_afk(self):
        self.prefs["afk"] = not self.prefs.get("afk")
        self.save_prefs()
        if self.running():
            self.send("afk")
        self.paint_afk(self.prefs["afk"])

    def paint_afk(self, on):
        self.afk_btn.set("AFK ON" if on else "AFK OFF", GREEN if on else GREY)

    def on_pause(self):
        if self.running():
            self.send("pause")

    def open_game(self):
        if not game_open():
            try:
                os.startfile(STEAM_URL)
            except OSError:
                return self.toast("Couldn't start Steam. Open BTD6 yourself.")
            self.toast("Opening BTD6...")

    def on_start(self):
        if self.waiting_since:              # waiting for the game: Start again cancels
            self.waiting_since = None
            return self.toast("Cancelled.")
        if self.running():
            self.send("stop")
            self.stop_at = time.time()
            return
        if not game_open():
            self.open_game()
            self.waiting_since = time.time()
            self.game_seen = None
            return
        self.launch_farm()

    def launch_farm(self):
        try:
            os.remove(CMD_FILE)
        except OSError:
            pass
        arg = "bonus" if self.prefs["mode"] == "bonus" else self.prefs.get("map")
        args = [sys.executable, os.path.join(HERE, "watchdog.py"), arg] + (["afk"] if self.prefs.get("afk") else [])
        env = dict(os.environ)
        uv = find_uv()
        if uv:      # the watchdog starts each farm with `uv run`
            env["PATH"] = os.path.dirname(uv) + os.pathsep + env.get("PATH", "")
        env.pop("VIRTUAL_ENV", None)
        self.proc = subprocess.Popen(args, cwd=HERE, env=env, creationflags=NO_WINDOW,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.stop_at = None

    CHECK_EVERY = 5 * 3600 * 1000           # ms between quiet checks while the app is open

    def background(self, job, then, label):
        """Run job() (code, msg) off the UI thread, then then(code, msg) on it."""
        self.updating = True
        self.update_btn.set(label, BLUE, enabled=False)

        def run():
            try:
                code, msg = job()
            except Exception as e:
                code, msg = 1, f"Update failed: {e}"
            self.root.after(0, lambda: then(code, msg))
        threading.Thread(target=run, daemon=True).start()

    def show_update_btn(self, label=None):
        """The button always names what a press does: CHECK UPDATE, UPDATE, RESTART. A check's
        result (UP TO DATE) shows for 3 s, then it's CHECK UPDATE again (user, 2026-11-08)."""
        if self.restart_ready:
            self.update_btn.set("RESTART", GREEN, enabled=True)
        elif self.update_ready:
            self.update_btn.set("UPDATE", GREEN, enabled=True)
        else:
            self.update_btn.set(label or "CHECK UPDATE", BLUE, enabled=True)
            if label:
                self.root.after(3000, lambda: None if self.updating else self.show_update_btn())

    def do_update(self):
        if self.updating:
            return
        if self.restart_ready:
            return self.restart()
        if self.update_ready:
            return self.install()
        self.check_update()

    def install(self):
        if self.running():
            self.show_update_btn()
            return self.toast("Stop the farm first, then press UPDATE.")
        import updater
        self.background(updater.update, self.update_done, "UPDATING...")

    def check_update(self, install=True):
        """CHECKING... -> UP TO DATE, or straight into UPDATING... when there is one.
        install=False (the 5-hourly check): just turn the button into a green UPDATE."""
        if self.updating:
            return
        import updater

        def done(code, msg):
            self.updating = False
            if code == 3:
                self.update_ready = True
                if install and not self.running():
                    return self.install()
                return self.show_update_btn()
            if code == 0:
                if install and self.files_changed():     # already on disk, just not loaded yet
                    return self.update_done(2, "")
                return self.show_update_btn("UP TO DATE")
            self.show_update_btn()
            if install:
                self.toast(msg)
        self.background(updater.check, done, "CHECKING...")

    APP_FILES = ("gui.py", "keys.py", "updater.py")     # what the open app has loaded

    def files_changed(self):
        """The app's own files changed since it opened (a git pull, an edit): reopen to load them.
        The farms themselves load fresh every start, so only these matter."""
        for f in self.APP_FILES:
            try:
                if os.path.getmtime(os.path.join(HERE, f)) > OPENED:
                    return True
            except OSError:
                pass
        return False

    def check_often(self):
        if not (self.update_ready or self.restart_ready):
            self.check_update(install=False)
        self.root.after(self.CHECK_EVERY, self.check_often)

    def update_done(self, code, msg):
        self.updating = False
        if code == 2:                       # new files are in: reopen on them
            self.update_ready, self.restart_ready = False, True
            if not self.running():
                return self.restart()
            return self.show_update_btn()
        if code == 0:
            self.update_ready = False
            return self.show_update_btn("UP TO DATE")
        self.show_update_btn()
        self.toast(msg)

    def restart(self):
        if self.running():
            return self.toast("Stop the farm first, then press RESTART.")
        subprocess.Popen([sys.executable, os.path.abspath(__file__)], cwd=HERE, creationflags=NO_WINDOW)
        self.root.destroy()

    def toast(self, msg):
        t = text_img(msg, 19, max_w=W - 120)
        p = ImageTk.PhotoImage(compose(plate(t.width + 50, t.height + 26, fill="#0b2350"), (t, "center")))
        self.keep.append(p)
        i = self.cv.create_image(W // 2, H - 64, image=p, anchor="s")
        self.root.after(5000, lambda: self.cv.delete(i))

    def on_close(self):
        if self.running():
            stop = read_json(os.path.join(HERE, "settings.json"), {}).get("stop") or "Numpad0"
            self.toast(f"The farm keeps running. Stop it with STOP or {stop}.")
            self.root.after(1800, self.root.destroy)
        else:
            self.root.destroy()

    # ---------------------------------------------------------------- log
    LOG_KEEP = 3000         # lines kept in the box; older ones drop off the top
    LOG_FIRST = 200_000     # bytes read when the app opens (the end of the file)

    @staticmethod
    def log_tag(line):
        low = line.lower()
        if line.startswith("!!") or "traceback" in low or "error" in low or "crash" in low or "lost" in low \
                or "gave up" in low or "failed" in low:
            return "err"
        if "won" in low or "victory" in low or "candy" in low:
            return "good"
        if "bonus" in low or "starting" in low or "afk" in low or "switch" in low or "stopped" in low \
                or "paused" in low or "resumed" in low or "rejoined" in low:
            return "info"
        if re.match(r"round \d+$", line.strip()) or "steps queued" in low:
            return "dim"
        return None

    def on_log_scroll(self, first, last):
        self.log_bar.set(first, last)
        self.log_follow = float(last) >= 0.999
        self.cv.itemconfigure(self.latest_btn.sprite.id, state="hidden" if self.log_follow else "normal")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.log_follow = True

    def jump_latest(self):
        self.log.see("end")
        self.log.xview_moveto(0)

    def read_log(self):
        """Append only what farm.log gained since the last look. A smaller file means it was
        rolled over (watchdog keeps it under 5 MB): start again from its top."""
        try:
            size = os.path.getsize(FARM_LOG)
        except OSError:
            size = 0
        fresh = size < self.log_pos or (self.log_pos == 0 and size)
        if size < self.log_pos:
            self.log_pos, self.log_rest = 0, ""
            self.log.configure(state="normal")
            self.log.delete("1.0", "end")
            self.log.configure(state="disabled")
        if size > self.log_pos:
            start = max(self.log_pos, size - self.LOG_FIRST) if self.log_pos == 0 else self.log_pos
            try:
                with open(FARM_LOG, "rb") as f:
                    f.seek(start)
                    data = f.read(size - start)
            except OSError:
                data = b""
            self.log_pos = start + len(data)
            text = self.log_rest + data.decode("utf-8", "replace")
            lines = text.split("\n")
            self.log_rest = lines.pop()
            if start and start != self.log_pos and fresh:
                lines = lines[1:]           # the first line read mid-file is a fragment
            if lines:
                follow = self.log_follow
                self.log.configure(state="normal")
                empty = self.log.index("end-1c") == "1.0"
                for i, line in enumerate(lines):
                    line = line.rstrip("\r")
                    self.log.insert("end", ("" if empty and i == 0 else "\n") + line, self.log_tag(line) or ())
                extra = int(self.log.index("end-1c").split(".")[0]) - self.LOG_KEEP
                if extra > 0:
                    self.log.delete("1.0", f"{extra + 1}.0")
                self.log.configure(state="disabled")
                if follow:
                    self.log.see("end")
                    self.log.xview_moveto(0)
        self.root.after(500, self.read_log)

    # ---------------------------------------------------------------- state
    def running(self):
        if self.proc and self.proc.poll() is None:
            return True
        st = read_json(STATE_FILE, {})
        return time.time() - st.get("heartbeat", 0) < 15 and not st.get("stats", {}).get("stopped")

    def current_script(self):
        for line in reversed(tail(WATCH_LOG, 40)):
            m = re.search(r"starting farm .*?(\w+\.py)(?:.*? @(easy|medium|hard))?", line)
            if m:
                return m.group(1) + (f"@{m.group(2)}" if m.group(2) else "")
        return None

    def refresh_tiles(self, playing=None):
        bonus = self.prefs["mode"] == "bonus"
        skip = {m for m, v in read_json(SKIP_FILE, {}).items() if time.time() - v.get("t", 0) < 6 * 3600}
        try:
            bonus_name = open(BONUS_FILE, encoding="utf-8").read().strip()
        except OSError:
            bonus_name = None
        for key, c in self.cells.items():
            c.set_state(chosen=not bonus and key == self.prefs.get("map"), playing=key == playing,
                        locked=ENTRIES[key][0] in skip)
        for name, spr in self.row_names.items():
            on = playing is not None and ENTRIES.get(playing, (None,))[0] == name
            st = (name in skip, bonus and name == bonus_name, on)
            spr.show((name,) + st, lambda n=name, st=st: self.row_label(n, *st))

    def row_label(self, name, locked, star_on, on):
        t = text_img(name, 18, fill="#9aa7bd" if locked else GOLD if on else "white", max_w=170)
        if not star_on:
            return t
        s_ = star(20)
        im = Image.new("RGBA", (t.width + 6 + s_.width, max(t.height, s_.height)), (0, 0, 0, 0))
        im.alpha_composite(t, (0, (im.height - t.height) // 2))
        im.alpha_composite(s_, (t.width + 6, (im.height - s_.height) // 2))
        return im

    def refresh(self):
        try:
            self._refresh()
        except Exception as e:      # one bad read must not kill the window
            print("refresh:", e)
        self.root.after(1000, self.refresh)

    def _refresh(self):
        st = read_json(STATE_FILE, {})
        stats = st.get("stats", {})
        on = self.running()
        status = stats.get("status", "") if on else ""
        paused = on and "PAUSED" in status.upper()
        stopping = on and self.stop_at
        if stopping and time.time() - self.stop_at > 10 and self.proc and self.proc.poll() is None:
            subprocess.run(["taskkill", "/f", "/t", "/pid", str(self.proc.pid)], capture_output=True,
                           creationflags=NO_WINDOW)
        if not on:
            self.stop_at = None

        game = game_open()
        self.game_btn.set("BTD6 OPEN" if game else "BTD6 CLOSED", GREEN if game else RED)
        if self.waiting_since:              # Start was pressed with the game closed
            if game and not self.game_seen:
                self.game_seen = time.time()
            if self.game_seen and time.time() - self.game_seen >= GAME_LOAD:
                self.waiting_since = None
                self.launch_farm()
            elif time.time() - self.waiting_since > 300:
                self.waiting_since = None
                self.toast("BTD6 didn't open. Open it, then press START.")

        label, style = (("STOPPING", YELLOW) if stopping else ("PAUSED", YELLOW) if paused
                        else ("RUNNING", GREEN) if on else ("WAITING", YELLOW) if self.waiting_since
                        else ("STOPPED", GREY))
        self.pill.show(label, lambda: compose(btd_button(150, 42, style, r=21),
                                              (text_img(label, 19, stroke=style["ink"]), "center")))
        self.start_btn.set("STOP" if on else "CANCEL" if self.waiting_since else "START",
                           RED if on else YELLOW if self.waiting_since else GREEN)
        self.pause_btn.set("RESUME" if paused else "PAUSE", YELLOW, enabled=bool(on))
        self.update_btn.set(enabled=not self.updating)
        self.paint_afk(bool(stats.get("afk")) if on else bool(self.prefs.get("afk")))

        vals = {"wins": str(stats.get("wins", 0)), "losses": str(stats.get("losses", 0)),
                "candy": f"{stats.get('candy', 0):,}",
                "time": hms(time.time() - stats["start"]) if on and stats.get("start") else "-"}
        colors = {"wins": "#8cf29a", "losses": "#ff9a9a", "candy": GOLD, "time": "#ffffff"}
        for k, v in vals.items():
            self.stats[k].show(v, lambda k=k, v=v: text_img(v, 32, fill=colors[k], max_w=124))

        playing = self.current_script() if on else None
        if status == "checking the event":      # this farm may not be the event's map: don't name it yet
            playing = None
        info = ENTRIES.get(playing or (None if self.prefs["mode"] == "bonus" else self.prefs.get("map")))
        title = f"{info[0]} · {info[1]}".upper() if info else "EVENT MODE"
        self.now_map.show(title, lambda: text_img(title, 34, max_w=530))
        s = (status or "").capitalize() if on else "Not running"
        self.now_status.show(s, lambda: text_img(s, 17, fill=CREAM, sw=0, shadow=False, max_w=530))
        nxt = stats.get("next") if on else None
        n = f"NEXT: {nxt}" if nxt else ""
        self.now_next.show(n, lambda: text_img(n, 20, fill=GOLD, max_w=530) if n
                           else Image.new("RGBA", (1, 1)))
        self.refresh_tiles(playing)


if __name__ == "__main__":
    App().root.mainloop()
