# BTD6-Autofarm

AFK farms for Bloons TD 6. They read the screen and click like a player would.

| Script | Map | Mode |
|---|---|---|
| `farm.py` | Infernal | Easy, Deflation |
| `flooded.py` | Flooded Valley | Easy, Deflation |
| `impoppable.py` | Infernal | Hard, Impoppable (Benjamin) |
| `dark.py` | Dark Castle | Hard, Impoppable (Striker Jones) |

## Requirements

| | |
|---|---|
| Platform | Windows 10 or 11 (uses Windows input, window and OCR APIs) |
| Game | Bloons TD 6 on Steam. Tested on Steam build 26122510 (updated 2026-10-22) |
| Resolution | 1920x1080, fullscreen or borderless, on the main monitor. Positions scale to other 16:9 sizes but only 1920x1080 is tested |
| Display scaling | Any (the scripts are DPI aware) |
| Language | Game in English, and the English Windows OCR language pack installed |
| Python | 3.12 (tested 3.12.15), run through [uv](https://docs.astral.sh/uv/) 0.13 or newer |
| Hotkeys | BTD6 defaults: towers on their default keys, upgrades `,` `.` `/`, targeting `Tab`, hero `U` |
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

## Running

Start BTD6 on the home screen, then run a farm under the watchdog, which restarts it if it crashes or stalls and relaunches the game through Steam:

```
uv run watchdog.py dark.py
```

Numpad 1 pauses and resumes, Numpad 0 stops. The farm only acts while BTD6 is the front window.
