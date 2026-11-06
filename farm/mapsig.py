"""Which Expert map a map-list tile shows, by its picture: works in any game language.

The tile's map picture is the same in every language (only its title is translated). The references
in assets/maps/ were cut from the Expert map list; tiles in the event's list are the same size.
A tile is compared after evening out its brightness and contrast, so a highlighted tile still matches.
"""
import os

from PIL import Image, ImageStat

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "assets", "maps")
BOX = (-160, -90, 60, 50)       # around the tile's centre: the map, clear of the title, medals and badges
SIZE = (22, 14)
MAX_DIST = 0.55                 # nearer than this to a reference = that map
MARGIN = 0.15                   # and this much nearer than to the next map


def fname(name):
    return "".join(c if c.isalnum() else "_" for c in name) + ".png"


def crop(im, centre):
    x, y = centre
    return im.crop((x + BOX[0], y + BOX[1], x + BOX[2], y + BOX[3]))


def sig(img):
    """The tile picture shrunk, each colour channel evened out to mean 0, spread 1."""
    small = img.convert("RGB").resize(SIZE, Image.BOX)
    st = ImageStat.Stat(small)
    px = list(small.getdata())
    return [[(p[c] - st.mean[c]) / (st.stddev[c] or 1) for c in range(3)] for p in px]


def dist(a, b):
    return sum(abs(x - y) for p, q in zip(a, b) for x, y in zip(p, q)) / (len(a) * 3)


_refs = {}


def refs():
    if not _refs:
        try:
            files = os.listdir(DIR)
        except OSError:
            files = []
        for f in files:
            if f.endswith(".png"):
                _refs[f[:-4]] = sig(Image.open(os.path.join(DIR, f)))
    return _refs


def which(im, centre, names=None):
    """The map whose name (from `names`, else the file names) matches the tile at centre, or None."""
    s = sig(crop(im, centre))
    lookup = {fname(n)[:-4]: n for n in (names or [])}
    ranked = sorted((dist(s, r), k) for k, r in refs().items())
    if not ranked:
        return None
    d, k = ranked[0]
    nxt = ranked[1][0] if len(ranked) > 1 else 9
    if d < MAX_DIST and nxt - d > MARGIN:
        return lookup.get(k, k)
    return None
