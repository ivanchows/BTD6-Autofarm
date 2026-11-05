# BTD6-Autofarm

Plays Bloons TD 6 for you while you're away.

[![Download](https://img.shields.io/badge/Download-ZIP-2ea44f?style=for-the-badge&logo=github)](https://github.com/ivanchows/BTD6-Autofarm/archive/refs/heads/main.zip)

## Setup (once)

1. Click **Download** above and unzip it.
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
3. In BTD6, set the game to **1920x1080** and **English**.
4. Keep the **default keybinds**, but set these 3 yourself (they start blank):

| Monkey | Key |
|---|---|
| Desperado | `;` |
| Mermonkey | `O` |
| Skywarden | `P` |

## Play

1. Open BTD6 and go to the home screen.
2. Open a terminal in the folder and type:

```
uv run watchdog.py sanctuary_deflation.py
```

Swap `sanctuary_deflation.py` for any map below.

| Keys | What it does |
|---|---|
| `Numpad 1` | Pause / go |
| `Numpad 0` | Stop |

No numpad? Open `keys.json` and pick other keys, like this:

```
{
  "pause": "F9",
  "stop": "F10"
}
```

Pick keys the game doesn't use. Moving the mouse to the top-left corner also stops it.

It only plays while BTD6 is on your screen. Tab out and it waits.

## Maps

| File | Map | Mode |
|---|---|---|
| `infernal_easy.py` | Infernal | Easy, Deflation |
| `flooded_easy.py` | Flooded Valley | Easy, Deflation |
| `sanctuary_deflation.py` | Sanctuary | Easy, Deflation |
| `ravine_deflation.py` | Ravine | Easy, Deflation |
| `quad_easy.py` | Quad | Easy |
| `workshop_easy.py` | Workshop | Easy |
| `dark_dungeons_easy.py` | Dark Dungeons | Easy |
| `bloody_puddles_easy.py` | Bloody Puddles | Easy |
| `tricky_tracks_easy.py` | Tricky Tracks | Easy |
| `ouch_easy.py` | #Ouch | Easy |
| `infernal_impop.py` | Infernal | Impoppable |
| `dark_castle_impop.py` | Dark Castle | Impoppable |
| `muddy_puddles_impop.py` | Muddy Puddles | Impoppable |
| `glacial_trail_impop.py` | Glacial Trail | Impoppable |
| `sanctuary_impop.py` | Sanctuary | Impoppable |

You need the map, the hero and the upgrades unlocked.
