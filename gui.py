# /// script
# dependencies = ["customtkinter"]
# ///
"""BTD6 Autofarm app: pick a map (or the bonus map), Start / Pause / Stop, AFK mode,
live stats and the farm's log. Open it with Autofarm.bat.

It runs watchdog.py like Play.bat does. Buttons reach the running farm through gui_cmd.txt
(core.gui_command), so they also work on a farm started from Play.bat."""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

import customtkinter as ctk

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "state.json")
FARM_LOG = os.path.join(HERE, "farm.log")
WATCH_LOG = os.path.join(HERE, "watchdog.log")
CMD_FILE = os.path.join(HERE, "gui_cmd.txt")
PREFS = os.path.join(HERE, "gui.json")
SKIP_FILE = os.path.join(HERE, "skipped_maps.json")
BONUS_FILE = os.path.join(HERE, "bonus_map.txt")
NO_WINDOW = 0x08000000

MAPS = [  # file, map, mode, hero
    ("infernal_easy.py", "Infernal", "Deflation", None),
    ("flooded_easy.py", "Flooded Valley", "Deflation", None),
    ("sanctuary_deflation.py", "Sanctuary", "Deflation", "Obyn"),
    ("ravine_deflation.py", "Ravine", "Deflation", "Obyn"),
    ("quad_easy.py", "Quad", "Easy", "Etienne"),
    ("workshop_easy.py", "Workshop", "Easy", "Sauda"),
    ("dark_dungeons_easy.py", "Dark Dungeons", "Easy", "Obyn"),
    ("bloody_puddles_easy.py", "Bloody Puddles", "Easy", None),
    ("tricky_tracks_easy.py", "Tricky Tracks", "Easy", "Quincy"),
    ("ouch_easy.py", "#Ouch", "Easy", None),
    ("infernal_impop.py", "Infernal", "Impoppable", "Benjamin"),
    ("dark_castle_impop.py", "Dark Castle", "Impoppable", "Striker Jones"),
    ("muddy_puddles_impop.py", "Muddy Puddles", "Impoppable", "Psi"),
    ("glacial_trail_impop.py", "Glacial Trail", "Impoppable", "Silas"),
    ("sanctuary_impop.py", "Sanctuary", "Impoppable", "Obyn"),
]
MODE_COLOR = {"Easy": "#3fb950", "Deflation": "#58a6ff", "Impoppable": "#f85149"}

BG = "#0f1320"
PANEL = "#181e2e"
CARD = "#212a3f"
CARD_HI = "#2c3856"
TEXT = "#e6e9f2"
DIM = "#8a93a8"
GOLD = "#f5c518"
GREEN = "#2ea043"
GREEN_HI = "#3fb950"
RED = "#da3633"
RED_HI = "#f85149"


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


def hms(sec):
    sec = int(max(0, sec))
    return f"{sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}"


class Tile(ctk.CTkFrame):
    def __init__(self, master, label, color=TEXT):
        super().__init__(master, fg_color=CARD, corner_radius=14)
        self.value = ctk.CTkLabel(self, text="-", font=("Segoe UI", 30, "bold"), text_color=color)
        self.value.pack(pady=(14, 0))
        ctk.CTkLabel(self, text=label, font=("Segoe UI", 13), text_color=DIM).pack(pady=(0, 12))

    def set(self, v):
        if self.value.cget("text") != v:
            self.value.configure(text=v)


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title("BTD6 Autofarm")
        self.geometry("1060x700")
        self.minsize(900, 600)
        self.prefs = read_json(PREFS, {"mode": "Bonus map", "map": "muddy_puddles_impop.py", "afk": False})
        self.proc = None
        self.log_sig = None
        self.log_sig_first = True
        self.map_rows = {}
        self.updating = False

        self.grid_columnconfigure(0, weight=0, minsize=380)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._header()
        self._left()
        self._right()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh()

    # ---------------------------------------------------------------- layout
    def _header(self):
        h = ctk.CTkFrame(self, fg_color="transparent")
        h.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 8))
        ctk.CTkLabel(h, text="BTD6 Autofarm", font=("Segoe UI", 26, "bold"), text_color=GOLD).pack(side="left")
        self.pill = ctk.CTkLabel(h, text="Stopped", font=("Segoe UI", 13, "bold"), corner_radius=12,
                                 fg_color=CARD, text_color=DIM, width=110, height=28)
        self.pill.pack(side="left", padx=14)
        self.update_btn = ctk.CTkButton(h, text="Update", width=100, height=32, fg_color=CARD,
                                        hover_color=CARD_HI, command=self.do_update)
        self.update_btn.pack(side="right")

    def _left(self):
        L = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=16)
        L.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))
        L.grid_rowconfigure(1, weight=1)
        L.grid_columnconfigure(0, weight=1)

        self.mode = ctk.CTkSegmentedButton(L, values=["Bonus map", "Pick a map"], height=36,
                                           font=("Segoe UI", 14, "bold"), command=self.on_mode,
                                           selected_color=GOLD, selected_hover_color="#ffd84d",
                                           unselected_color=CARD, text_color=TEXT)
        self.mode.set(self.prefs.get("mode", "Bonus map"))
        self.mode.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))

        self.list = ctk.CTkScrollableFrame(L, fg_color="transparent")
        self.list.grid(row=1, column=0, sticky="nsew", padx=6)
        self.list.grid_columnconfigure(0, weight=1)
        for i, (fn, name, mode, hero) in enumerate(MAPS):
            row = ctk.CTkFrame(self.list, fg_color=CARD, corner_radius=10, height=46, cursor="hand2")
            row.grid(row=i, column=0, sticky="ew", padx=6, pady=3)
            row.grid_columnconfigure(1, weight=1)
            bar = ctk.CTkFrame(row, width=5, height=30, fg_color=MODE_COLOR[mode], corner_radius=3)
            bar.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(8, 10), pady=8)
            t = ctk.CTkLabel(row, text=name, font=("Segoe UI", 15, "bold"), text_color=TEXT, anchor="w")
            t.grid(row=0, column=1, sticky="w", pady=(6, 0))
            s = ctk.CTkLabel(row, text=mode + (f"  ·  {hero}" if hero else ""), font=("Segoe UI", 12),
                             text_color=DIM, anchor="w")
            s.grid(row=1, column=1, sticky="w", pady=(0, 6))
            tag = ctk.CTkLabel(row, text="", font=("Segoe UI", 11, "bold"), corner_radius=8, height=22)
            tag.grid(row=0, column=2, rowspan=2, padx=10)
            for w in (row, bar, t, s, tag):
                w.bind("<Button-1>", lambda e, f=fn: self.pick(f))
            self.map_rows[fn] = (row, tag, name)

        c = ctk.CTkFrame(L, fg_color="transparent")
        c.grid(row=2, column=0, sticky="ew", padx=14, pady=14)
        c.grid_columnconfigure((0, 1), weight=1)
        self.afk = ctk.CTkSwitch(c, text="AFK mode", font=("Segoe UI", 14), progress_color=GOLD,
                                 command=self.on_afk)
        if self.prefs.get("afk"):
            self.afk.select()
        self.afk.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        self.start_btn = ctk.CTkButton(c, text="Start", height=52, font=("Segoe UI", 20, "bold"),
                                       fg_color=GREEN, hover_color=GREEN_HI, corner_radius=12,
                                       command=self.on_start)
        self.start_btn.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.pause_btn = ctk.CTkButton(c, text="Pause", height=52, font=("Segoe UI", 20, "bold"),
                                       fg_color=CARD, hover_color=CARD_HI, corner_radius=12,
                                       command=self.on_pause)
        self.pause_btn.grid(row=1, column=1, sticky="ew", padx=(6, 0))

    def _right(self):
        R = ctk.CTkFrame(self, fg_color="transparent")
        R.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        R.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="t")
        R.grid_rowconfigure(2, weight=1)
        self.tiles = {
            "wins": Tile(R, "Wins", GREEN_HI), "losses": Tile(R, "Losses", RED_HI),
            "candy": Tile(R, "Candy", GOLD), "time": Tile(R, "Time"),
        }
        for i, t in enumerate(self.tiles.values()):
            t.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0 if i == 3 else 6))

        now = ctk.CTkFrame(R, fg_color=PANEL, corner_radius=16)
        now.grid(row=1, column=0, columnspan=4, sticky="ew", pady=12)
        self.map_lbl = ctk.CTkLabel(now, text="-", font=("Segoe UI", 20, "bold"), text_color=TEXT, anchor="w")
        self.map_lbl.pack(fill="x", padx=18, pady=(14, 0))
        self.status_lbl = ctk.CTkLabel(now, text="", font=("Segoe UI", 14), text_color=DIM, anchor="w")
        self.status_lbl.pack(fill="x", padx=18)
        self.next_lbl = ctk.CTkLabel(now, text="", font=("Segoe UI", 14), text_color=GOLD, anchor="w")
        self.next_lbl.pack(fill="x", padx=18, pady=(0, 14))

        self.log = ctk.CTkTextbox(R, fg_color=PANEL, corner_radius=16, font=("Consolas", 12),
                                  text_color="#c9d1e3", wrap="none")
        self.log.grid(row=2, column=0, columnspan=4, sticky="nsew")
        self.log.configure(state="disabled")

        keys = read_json(os.path.join(HERE, "settings.json"), {})
        k = lambda n, d: (keys.get(n) or d)
        ctk.CTkLabel(R, text=f"{k('pause', 'Numpad1')} pause   ·   {k('stop', 'Numpad0')} stop   ·   "
                              f"{k('afk', 'Numpad2')} AFK", font=("Segoe UI", 12), text_color=DIM
                     ).grid(row=3, column=0, columnspan=4, pady=(8, 0))

    # ---------------------------------------------------------------- actions
    def save_prefs(self):
        self.prefs.update(mode=self.mode.get(), afk=bool(self.afk.get()))
        try:
            with open(PREFS, "w", encoding="utf-8") as f:
                json.dump(self.prefs, f)
        except OSError:
            pass

    def pick(self, fn):
        if self.running():
            return
        self.prefs["map"] = fn
        self.mode.set("Pick a map")
        self.save_prefs()
        self.paint_maps()

    def on_mode(self, _):
        self.save_prefs()
        self.paint_maps()

    def send(self, word):
        with open(CMD_FILE, "w", encoding="utf-8") as f:
            f.write(word)

    def on_afk(self):
        self.save_prefs()
        st = read_json(STATE_FILE, {}).get("stats", {})
        if self.running() and bool(st.get("afk")) != bool(self.afk.get()):
            self.send("afk")

    def on_pause(self):
        if self.running():
            self.send("pause")

    def on_start(self):
        if self.running():
            self.send("stop")
            self.stop_at = time.time()
            return
        try:
            os.remove(CMD_FILE)
        except OSError:
            pass
        arg = "bonus" if self.mode.get() == "Bonus map" else self.prefs.get("map")
        args = [sys.executable, os.path.join(HERE, "watchdog.py"), arg] + (["afk"] if self.afk.get() else [])
        env = dict(os.environ)
        uv = find_uv()
        if uv:      # the watchdog starts each farm with `uv run`
            env["PATH"] = os.path.dirname(uv) + os.pathsep + env.get("PATH", "")
        env.pop("VIRTUAL_ENV", None)
        self.proc = subprocess.Popen(args, cwd=HERE, env=env, creationflags=NO_WINDOW,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.stop_at = None

    def do_update(self):
        if self.running() or self.updating:
            return
        self.updating = True
        self.update_btn.configure(text="Updating...")

        def run():
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                os.path.join(HERE, "updater.ps1")], cwd=HERE, capture_output=True,
                               text=True, creationflags=NO_WINDOW)
            msg = (r.stdout.strip().splitlines() or ["done"])[-1]
            self.after(0, lambda: self.update_done(msg))
        threading.Thread(target=run, daemon=True).start()

    def update_done(self, msg):
        self.updating = False
        self.update_btn.configure(text="Update")
        self.toast(msg + ("  Reopen the app to use it." if msg.startswith("Updated") else ""))

    def toast(self, msg):
        t = ctk.CTkLabel(self, text=msg, font=("Segoe UI", 13, "bold"), fg_color=CARD_HI,
                         corner_radius=10, text_color=TEXT, height=36)
        t.place(relx=0.5, rely=0.96, anchor="s")
        self.after(5000, t.destroy)

    def on_close(self):
        if self.running():
            self.toast("The farm keeps running. Stop it with Stop or " +
                       (read_json(os.path.join(HERE, "settings.json"), {}).get("stop") or "Numpad0") + ".")
            self.after(1800, self.destroy)
        else:
            self.destroy()

    # ---------------------------------------------------------------- state
    def running(self):
        if self.proc and self.proc.poll() is None:
            return True
        st = read_json(STATE_FILE, {})
        return time.time() - st.get("heartbeat", 0) < 15 and not st.get("stats", {}).get("stopped")

    def current_script(self):
        for line in reversed(tail(WATCH_LOG, 40)):
            m = re.search(r"starting farm .*?([\w]+\.py)", line)
            if m:
                return m.group(1)
        return None

    def paint_maps(self, playing=None):
        bonus = self.mode.get() == "Bonus map"
        skip = {m for m, v in read_json(SKIP_FILE, {}).items() if time.time() - v.get("t", 0) < 6 * 3600}
        try:
            bonus_name = open(BONUS_FILE, encoding="utf-8").read().strip()
        except OSError:
            bonus_name = None
        for fn, (row, tag, name) in self.map_rows.items():
            chosen = (not bonus and fn == self.prefs.get("map"))
            row.configure(fg_color=CARD_HI if chosen or fn == playing else CARD,
                          border_width=2 if chosen else 0, border_color=GOLD)
            if fn == playing:
                tag.configure(text=" PLAYING ", fg_color=GREEN, text_color="white")
            elif name in skip:
                tag.configure(text=" LOCKED ", fg_color="#3a2a2a", text_color=RED_HI)
            elif bonus and name == bonus_name:
                tag.configure(text=" BONUS ", fg_color=GOLD, text_color="#1a1a1a")
            else:
                tag.configure(text="", fg_color="transparent")

    def refresh(self):
        try:
            self._refresh()
        except Exception as e:      # never let one bad read kill the window
            print("refresh:", e)
        self.after(1000, self.refresh)

    def _refresh(self):
        st = read_json(STATE_FILE, {})
        stats = st.get("stats", {})
        on = self.running()
        status = stats.get("status", "") if on else ""
        paused = on and "PAUSED" in status.upper()
        stopping = on and getattr(self, "stop_at", None)
        if stopping and time.time() - self.stop_at > 10 and self.proc and self.proc.poll() is None:
            subprocess.run(["taskkill", "/f", "/t", "/pid", str(self.proc.pid)], capture_output=True,
                           creationflags=NO_WINDOW)
        if not on:
            self.stop_at = None

        if stopping:
            self.pill.configure(text="Stopping", fg_color="#4a3a12", text_color=GOLD)
        elif paused:
            self.pill.configure(text="Paused", fg_color="#4a3a12", text_color=GOLD)
        elif on:
            self.pill.configure(text="Running", fg_color="#123a1e", text_color=GREEN_HI)
        else:
            self.pill.configure(text="Stopped", fg_color=CARD, text_color=DIM)
        self.start_btn.configure(text="Stop" if on else "Start", fg_color=RED if on else GREEN,
                                 hover_color=RED_HI if on else GREEN_HI)
        self.pause_btn.configure(text="Resume" if paused else "Pause",
                                 state="normal" if on else "disabled")
        self.update_btn.configure(state="disabled" if on or self.updating else "normal")
        if on and bool(stats.get("afk")) != bool(self.afk.get()):
            (self.afk.select if stats.get("afk") else self.afk.deselect)()

        self.tiles["wins"].set(str(stats.get("wins", 0)))
        self.tiles["losses"].set(str(stats.get("losses", 0)))
        self.tiles["candy"].set(f"{stats.get('candy', 0):,}")
        self.tiles["time"].set(hms(time.time() - stats["start"]) if on and stats.get("start") else "-")

        playing = self.current_script() if on else None
        info = next((m for m in MAPS if m[0] == playing), None)
        self.map_lbl.configure(text=f"{info[1]}  ·  {info[2]}" if info else ("Bonus map" if self.mode.get() == "Bonus map" else
                               next((f"{m[1]}  ·  {m[2]}" for m in MAPS if m[0] == self.prefs.get("map")), "-")))
        self.status_lbl.configure(text=status.capitalize() if on else "Not running")
        nxt = stats.get("next") if on else None
        self.next_lbl.configure(text=f"Next: {nxt}" if nxt else "")
        self.paint_maps(playing)

        try:
            sig = (os.path.getsize(FARM_LOG), os.path.getmtime(FARM_LOG))
        except OSError:
            sig = None
        if sig != self.log_sig:
            self.log_sig = sig
            lines = tail(FARM_LOG, 300)
            at_end = self.log.yview()[1] > 0.98 or self.log_sig_first
            self.log_sig_first = False
            self.log.configure(state="normal")
            self.log.delete("1.0", "end")
            self.log.insert("end", "\n".join(lines))
            self.log.configure(state="disabled")
            if at_end:
                self.log.see("end")


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    App().mainloop()
