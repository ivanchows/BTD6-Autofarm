# BTD6-Autofarm for Candies Expert Maps

Farms candies for you while you're away.
Combinations of easy and impoppable maps.

<a href="https://github.com/ivanchows/BTD6-Autofarm/archive/refs/heads/main.zip"><img src="https://img.shields.io/badge/Download-ZIP-2ea44f?style=for-the-badge&logo=github" alt="Download" height="110"></a>

## Setup (once)

1. Click **Download** above and unzip it.
2. Double-click **Install.bat** (it installs [uv](https://docs.astral.sh/uv/), which runs the farm). The app opens when it's done.
   Windows may say it protected your PC (the app isn't signed): click **More info**, then **Run anyway**.
   If it says it couldn't install uv, check your internet or antivirus and run it again.
3. In BTD6, set the game to **1920x1080**. Any game language works: in a new language the first game is a little slower while the farm learns its words.
4. Keep the **default keybinds**, but set these 3 yourself (they start blank):

| Monkey | Key |
|---|---|
| Desperado | `;` |
| Mermonkey | `O` |
| Skywarden | `P` |

## Update

The app checks for an update every time it opens, installs it and reopens by itself. While it's open it checks every 5 hours: **CHECK UPDATE** turns into a green **UPDATE** when there is one. Your stats and settings are kept.
(Or stop the farm and double-click **farm\Updater.bat**.)

## Play

1. Open BTD6 and go to the home screen.
2. Double-click **Autofarm.exe**. Turn on **Event mode** (it plays the map with **bonus rewards** in the candy event and switches maps by itself) or pick a map, then press **Start**. BTD6 closed? Start opens it first.

Or double-click **farm\Play.bat** to start event mode without the app.

Want one map only? Pick it in the app, or open a terminal in the **farm** folder and type (swap the file for any map below):

```
uv run watchdog.py sanctuary_deflation.py
```

| Keys | What it does |
|---|---|
| `Numpad 1` | Pause / go |
| `Numpad 0` | Stop |
| `Numpad 2` | AFK mode on / off |

Change these in the app (the buttons under the log), or in `farm\settings.json`:

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

| Map | File | Modes | Hero |
|---|---|---|---|
| Infernal | `infernal_impop.py` | Impoppable ★, Hard, Medium, Easy | Benjamin |
| Infernal | `infernal_easy.py` | Deflation | none |
| Flooded Valley | `flooded_valley_impop.py` | Easy ★, Medium | Etienne |
| Flooded Valley | `flooded_easy.py` | Deflation | none |
| Sanctuary | `sanctuary_impop.py` | Impoppable, Hard, Medium, Easy | Obyn |
| Sanctuary | `sanctuary_deflation.py` | Deflation ★ | Obyn |
| Ravine | `ravine_deflation.py` | Deflation ★ | Obyn |
| Dark Castle | `dark_castle_impop.py` | Impoppable ★, Hard, Medium, Easy | Striker Jones |
| Dark Castle | `dark_castle_deflation.py` | Deflation | none |
| Muddy Puddles | `muddy_puddles_impop.py` | Impoppable ★, Hard, Medium, Easy | Psi |
| Glacial Trail | `glacial_trail_impop.py` | Impoppable ★, Hard, Medium, Easy | Silas |
| Quad | `quad_easy.py` | Easy ★ | Etienne |
| Workshop | `workshop_easy.py` | Easy ★ | Sauda |
| Dark Dungeons | `dark_dungeons_easy.py` | Easy ★ | Obyn |
| Bloody Puddles | `bloody_puddles_easy.py` | Easy ★ | none |
| Tricky Tracks | `tricky_tracks_easy.py` | Easy ★ | Quincy |
| #Ouch | `ouch_easy.py` | Easy ★ | none |

★ = what Event mode plays on that map. Easy, Medium and Hard are Standard games.
From a terminal, add the mode to an Impoppable file: `uv run watchdog.py flooded_valley_impop.py@easy`.

## Heroes you need

Obyn, Etienne, Sauda, Quincy, Striker Jones, Benjamin, Psi, Silas.

The farm picks the right hero by itself. You just need them unlocked.

Missing a map or a hero? The farm skips that map. In bonus mode it plays a map you do have
until the bonus moves on. It tries a skipped map again after 6 hours.

You need the map, the hero and the upgrades unlocked.
