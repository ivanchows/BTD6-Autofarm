"""Picture checks that work in any game language.

BTD6 can run in 23 languages, and Windows' OCR only reads the user's own. So instead of reading words,
the farm learns what a word LOOKS like (a tower's name on its upgrade panel, a targeting label) the first
time it knows what it is, and later compares pictures. What it learns is kept per game language in
learned/<id>/, so a second game in the same language starts out knowing everything.

The language is told by the PLAY button on the home screen (its label is in the game's language).
"""
import os

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "learned")
PLAY_LABEL = (840, 1010, 1080, 1062)        # the word under the big green Play button (1920x1080)
SAME = 0.06                                 # the same word re-read measured 0.000; different words 0.133+ (Japanese)


def mask(im, box, light=200):
    """The light (white) letters in box as a 1-bit-like L image: 255 = letter."""
    return im.crop(box).convert("L").point(lambda p: 255 if p > light else 0)


def ink(m):
    return m.histogram()[255]


def diff(a, b):
    """0 = the same picture, 1 = nothing in common. Allows a few pixels of shift either way."""
    if a.size != b.size:
        b = b.resize(a.size)
    na, nb = ink(a), ink(b)
    if not na or not nb:
        return 1.0
    best = 1.0
    for sx in (-4, -2, 0, 2, 4):
        for sy in (-2, 0, 2):
            d = ImageChops.difference(a, ImageChops.offset(b, sx, sy)).histogram()[255]
            best = min(best, d / (na + nb))
    return best


def same(a, b):
    return diff(a, b) < SAME


# --- which language: one folder per PLAY label seen ------------------------------------------------
_lang = {"id": None}


def _read_current():
    try:
        return open(os.path.join(DIR, "current.txt"), encoding="utf-8").read().strip() or None
    except OSError:
        return None


def note_home(im):
    """Call on the home screen: picks (or makes) the folder for the language now on."""
    m = mask(im, PLAY_LABEL)
    if ink(m) < 40:
        return
    os.makedirs(DIR, exist_ok=True)
    found = None
    for d in sorted(os.listdir(DIR)):
        p = os.path.join(DIR, d, "_play.png")
        if os.path.isfile(p):
            try:
                if same(m, Image.open(p).convert("L")):
                    found = d
                    break
            except OSError:
                pass
    if found is None:
        n = 1
        while os.path.exists(os.path.join(DIR, f"lang{n}")):
            n += 1
        found = f"lang{n}"
        os.makedirs(os.path.join(DIR, found))
        m.save(os.path.join(DIR, found, "_play.png"))
        print(f"new game language seen: learning its words in learned/{found}")
    if found != _lang["id"]:
        _lang["id"] = found
        _cache.clear()
        with open(os.path.join(DIR, "current.txt"), "w", encoding="utf-8") as f:
            f.write(found)


def _folder():
    if _lang["id"] is None:
        _lang["id"] = _read_current() or "unknown"
    p = os.path.join(DIR, _lang["id"])
    os.makedirs(p, exist_ok=True)
    return p


# --- learned words: kind = "name" (tower, by its key) or "target" (a targeting mode) ---------------
_cache = {}


def _file(kind, word):
    safe = "".join(c if c.isalnum() else f"_{ord(c)}" for c in word)
    return os.path.join(_folder(), f"{kind}_{safe}.png")


def get(kind, word):
    k = (kind, word)
    if k not in _cache:
        try:
            _cache[k] = Image.open(_file(kind, word)).convert("L")
        except OSError:
            _cache[k] = None
    return _cache[k]


def put(kind, word, m):
    if ink(m) < 30:                 # nothing readable there: don't learn a blank
        return
    _cache[(kind, word)] = m
    try:
        m.save(_file(kind, word))
    except OSError:
        pass


def known(kind):
    """{word: mask} learned for this language."""
    out = {}
    try:
        names = os.listdir(_folder())
    except OSError:
        return out
    for f in names:
        if f.startswith(kind + "_") and f.endswith(".png"):
            w = f[len(kind) + 1:-4]
            word = ""
            i = 0
            while i < len(w):           # undo _file's escaping
                if w[i] == "_":
                    j = i + 1
                    while j < len(w) and w[j].isdigit():
                        j += 1
                    word += chr(int(w[i + 1:j]))
                    i = j
                else:
                    word += w[i]
                    i += 1
            m = get(kind, word)
            if m is not None:
                out[word] = m
    return out


def which(kind, m):
    """The learned word this picture shows, or None."""
    best, score = None, SAME
    for word, ref in known(kind).items():
        d = diff(m, ref)
        if d < score:
            best, score = word, d
    return best
