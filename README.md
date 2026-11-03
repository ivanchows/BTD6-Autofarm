# BTD6-Autofarm

AFK farms for Bloons TD 6 (1920x1080, Windows). Each script runs with `uv`, which installs its own dependencies.

| Script | Map | Mode |
|---|---|---|
| `farm.py` | Infernal | Easy, Deflation |
| `flooded.py` | Flooded Valley | Easy, Deflation |
| `impoppable.py` | Infernal | Hard, Impoppable (Benjamin) |
| `dark.py` | Dark Castle | Hard, Impoppable (Striker Jones) |

Run one under the watchdog, which restarts it if it crashes or stalls and relaunches the game through Steam:

```
uv run watchdog.py dark.py
```

Numpad 1 pauses and resumes, Numpad 0 stops. The farm only acts while BTD6 is the front window.
