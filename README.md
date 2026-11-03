# BTD6-Autofarm

AFK farms for Bloons TD 6. They read the screen and click like a player would.

Each map script is named `<map>_<mode>.py`. The shared code lives in `core.py` (menus, screens, OCR, stats box) and `infernal_impop.py` (checked placing and upgrading, which the other maps reuse).

| Script | Map | Mode |
|---|---|---|
| `infernal_easy.py` | Infernal | Easy, Deflation |
| `flooded_easy.py` | Flooded Valley | Easy, Deflation |
| `infernal_impop.py` | Infernal | Hard, Impoppable (Benjamin) |
| `dark_castle_impop.py` | Dark Castle | Hard, Impoppable (Striker Jones) |
| `quad_easy.py` | Quad | Easy, Standard (Etienne) |
| `muddy_puddles_impop.py` | Muddy Puddles | Hard, Impoppable (Psi) |
| `workshop_easy.py` | Workshop | Easy, Standard (Sauda) |

## Requirements

| | |
|---|---|
| Platform | Windows 10 or 11 (uses Windows input, window and OCR APIs) |
| Game | Bloons TD 6 on Steam. Tested on Steam build 26122510 (updated 2026-10-22) |
| Resolution | 1920x1080, fullscreen or borderless, on the main monitor. Positions scale to other 16:9 sizes but only 1920x1080 is tested |
| Display scaling | Any (the scripts are DPI aware) |
| Language | Game in English, and the English Windows OCR language pack installed |
| Python | 3.12 (tested 3.12.15), run through [uv](https://docs.astral.sh/uv/) 0.13 or newer |
| Hotkeys | BTD6 defaults (see [Hotkeys](#hotkeys)) |
| Unlocks | The maps, heroes and every upgrade each farm buys |

### Python dependencies

uv installs these on the first run (they're declared at the top of each script):

- `mss`
- `pillow`
- `winrt-Windows.Media.Ocr`
- `winrt-Windows.Graphics.Imaging`
- `winrt-Windows.Storage.Streams`
- `winrt-Windows.Foundation`
- `winrt-Windows.Foundation.Collections`
- `winrt-Windows.Globalization`

## Hotkeys

The farms press the game's default keys, so keep these bound in BTD6's settings.

| Action | Key |
|---|---|
| Start round / fast forward | `Space` |
| Upgrade top / middle / bottom path | `,` `.` `/` |
| Next targeting | `Tab` |
| Hero | `U` |
| Hero and tower abilities | `1` `2` `3` (in the order they unlock) |

| Tower | Key | Tower | Key |
|---|---|---|---|
| Dart Monkey | `Q` | Monkey Buccaneer | `C` |
| Boomerang Monkey | `W` | Wizard Monkey | `A` |
| Bomb Shooter | `E` | Alchemist | `F` |
| Glue Gunner | `Y` | Druid | `G` |
| Desperado | `;` | Spike Factory | `J` |
| Sniper Monkey | `Z` | Monkey Village | `K` |
| Monkey Sub | `X` | Mermonkey | `O` |
| Skywarden | `P` | | |

The farm's own keys, read even while the game has focus:

| Key | Does |
|---|---|
| `Numpad 1` (or `End`) | Pause / resume |
| `Numpad 0` (or `Insert`, `F8`) | Stop the farm and the watchdog |
| `Ctrl` held | Drag the stats box |

## Running

Start BTD6 on the home screen, then run a farm under the watchdog, which restarts it if it crashes or stalls and relaunches the game through Steam:

```
uv run watchdog.py dark_castle_impop.py
```

Numpad 1 pauses and resumes, Numpad 0 stops. The farm only acts while BTD6 is the front window.

A stats box sits over the game: runs, uptime, XP, cash, and the next tower step (or "done"). Hold Ctrl to drag it; it remembers where you left it.
