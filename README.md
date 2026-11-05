# BTD6-Autofarm for Candies Expert Maps

Farms candies for you while you're away.
Combinations of easy and impoppable maps.

<a href="https://github.com/ivanchows/BTD6-Autofarm/archive/refs/heads/main.zip"><img src="https://img.shields.io/badge/Download-ZIP-2ea44f?style=for-the-badge&logo=github" alt="Download" height="110"></a>

## Setup (once)

1. Click **Download** above and unzip it.
2. Double-click **Install.bat** (it installs [uv](https://docs.astral.sh/uv/), which runs the farm).
   If it says it couldn't install uv, check your internet or antivirus and run it again.
3. In BTD6, set the game to **1920x1080** and **English**.
4. Keep the **default keybinds**, but set these 3 yourself (they start blank):

| Monkey | Key |
|---|---|
| Desperado | `;` |
| Mermonkey | `O` |
| Skywarden | `P` |

## Play

1. Open BTD6 and go to the home screen.
2. Double-click **Play.bat**. It plays the map with **bonus rewards** in the candy event and switches maps by itself.

Want one map only? Open a terminal in the folder and type (swap the file for any map below):

```
uv run watchdog.py sanctuary_deflation.py
```

| Keys | What it does |
|---|---|
| `Numpad 1` | Pause / go |
| `Numpad 0` | Stop |
| `Numpad 2` | AFK mode on / off |

Change these in `settings.json`:

```
{
  "pause": "F9",
  "stop": "F10",
  "afk": "F11"
}
```

No numpad? Pick other keys the game doesn't use. Moving the mouse to the top-left corner also stops it.

It only clicks while BTD6 is on your screen. Tab out and it waits, so you can do other things.

**AFK mode** (`Numpad 2`, or add `afk` to the command): it tabs back into BTD6 by itself 5 seconds after you leave. The info box says "AFK mode" while it's on.

## Maps

| File | Map | Mode | Hero |
|---|---|---|---|
| `infernal_easy.py` | Infernal | Easy, Deflation | none |
| `flooded_easy.py` | Flooded Valley | Easy, Deflation | none |
| `sanctuary_deflation.py` | Sanctuary | Easy, Deflation | Obyn |
| `ravine_deflation.py` | Ravine | Easy, Deflation | Obyn |
| `quad_easy.py` | Quad | Easy | Etienne |
| `workshop_easy.py` | Workshop | Easy | Sauda |
| `dark_dungeons_easy.py` | Dark Dungeons | Easy | Obyn |
| `bloody_puddles_easy.py` | Bloody Puddles | Easy | none |
| `tricky_tracks_easy.py` | Tricky Tracks | Easy | Quincy |
| `ouch_easy.py` | #Ouch | Easy | none |
| `infernal_impop.py` | Infernal | Impoppable | Benjamin |
| `dark_castle_impop.py` | Dark Castle | Impoppable | Striker Jones |
| `muddy_puddles_impop.py` | Muddy Puddles | Impoppable | Psi |
| `glacial_trail_impop.py` | Glacial Trail | Impoppable | Silas |
| `sanctuary_impop.py` | Sanctuary | Impoppable | Obyn |

## Heroes you need

Obyn, Etienne, Sauda, Quincy, Striker Jones, Benjamin, Psi, Silas.

The farm picks the right hero by itself. You just need them unlocked.

You need the map, the hero and the upgrades unlocked.
