#!/usr/bin/env python3
"""ChaosCatcher self-care suite GUI.

Simple Tkinter GUI wrapper around the ChaosCatcher JSON data used by the CLI.

Features implemented in GUI:
- Water intake logger + today's log + reset
- Mood quick logger
- Vyvanse status viewer
- Hemp logger
- Generic substance logger
- Summary tab similar to CLI summary
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tkinter as tk
from dataclasses import asdict, dataclass
from tkinter import messagebox, ttk
from typing import List, Optional

# Match CLI data path
DATA_PATH = os.environ.get(
    "CHAOSCATCHER_DATA", os.path.join(os.path.expanduser("~"), ".chaoscatcher.json")
)


# --------- dataclasses (mirror CLI) ---------
@dataclass
class WaterEntry:
    amount_ml: int
    timestamp: str


@dataclass
class HempEntry:
    amount_mg: int
    feeling: str
    outcome: str
    timestamp: str


@dataclass
class SubstanceEntry:
    name: str
    amount: str
    feeling: str
    outcome: str
    timestamp: str


@dataclass
class VyvanseState:
    pill_count: int
    daily_dosage: int
    refill_date: str


@dataclass
class VyvanseLog:
    change: int
    reason: str
    timestamp: str


# --------- helpers shared with CLI semantics ---------
def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="minutes")


def ensure_data_dir() -> None:
    directory = os.path.dirname(DATA_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)


def load_data() -> dict:
    ensure_data_dir()
    if not os.path.exists(DATA_PATH):
        # Default structure aligned with CLI
        return {
            "focus_sessions": [],
            "moods": [],
            "water": [],
            "vyvanse": asdict(
                VyvanseState(
                    pill_count=0,
                    daily_dosage=1,
                    refill_date=now_iso().split("T")[0],
                )
            ),
            "vyvanse_log": [],
            "hemp": [],
            "substances": [],
            "water_goal": 64,
        }
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Backward-compat guards
    data.setdefault("focus_sessions", [])
    data.setdefault("moods", [])
    data.setdefault("water", [])
    data.setdefault("hemp", [])
    data.setdefault("substances", [])
    data.setdefault("vyvanse_log", [])
    if "vyvanse" not in data:
        data["vyvanse"] = asdict(
            VyvanseState(
                pill_count=0,
                daily_dosage=1,
                refill_date=now_iso().split("T")[0],
            )
        )
    data.setdefault("water_goal", 64)
    return data


def save_data(data: dict) -> None:
    ensure_data_dir()
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_water_goal(data: Optional[dict] = None) -> int:
    if data is None:
        data = load_data()
    return data.get("water_goal", 64)


def get_water_today(data: Optional[dict] = None) -> int:
    if data is None:
        data = load_data()
    today = dt.date.today().isoformat()
    total = 0
    for entry in data.get("water", []):
        ts = entry.get("timestamp", "")
        date = ts.split("T")[0]
        if date == today:
            total += entry.get("amount_ml", 0)
    return total


def progress_bar(current: int, total: int, length: int = 20) -> str:
    if total <= 0:
        total = 1
    filled = int((current / total) * length)
    filled = max(0, min(length, filled))
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {current}/{total} oz"


def get_last_vyvanse_take(data: Optional[dict] = None) -> Optional[dt.datetime]:
    if data is None:
        data = load_data()
    log = data.get("vyvanse_log", [])
    for entry in reversed(log):
        reason = entry.get("reason", "")
        if reason.startswith("took"):
            ts = entry.get("timestamp")
            try:
                return dt.datetime.fromisoformat(ts)
            except Exception:
                return None
    return None


# --------- GUI app ---------
class ChaosCatcherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ChaosCatcher Self-Care")
        self.geometry("640x480")

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.water_frame = ttk.Frame(notebook)
        self.mood_frame = ttk.Frame(notebook)
        self.vyvanse_frame = ttk.Frame(notebook)
        self.hemp_frame = ttk.Frame(notebook)
        self.substance_frame = ttk.Frame(notebook)
        self.summary_frame = ttk.Frame(notebook)

        notebook.add(self.water_frame, text="Water")
        notebook.add(self.mood_frame, text="Mood")
        notebook.add(self.vyvanse_frame, text="Vyvanse")
        notebook.add(self.hemp_frame, text="Hemp")
        notebook.add(self.substance_frame, text="Substances")
        notebook.add(self.summary_frame, text="Summary")

        self._build_water_tab()
        self._build_mood_tab()
        self._build_vyvanse_tab()
        self._build_hemp_tab()
        self._build_substance_tab()
        self._build_summary_tab()

        # Bottom reset button for water
        reset_btn = ttk.Button(self, text="Reset Today's Water", command=self.reset_today_water)
        reset_btn.pack(side="bottom", pady=(0, 6))

        # Initial summary refresh
        self.refresh_summary()

    # ----- Water tab -----
    def _build_water_tab(self) -> None:
        f = self.water_frame

        row = 0
        ttk.Label(f, text="Log water (oz):").grid(row=row, column=0, sticky="w", padx=4, pady=4)
        self.water_amount_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.water_amount_var, width=10).grid(
            row=row, column=1, sticky="w", padx=4, pady=4
        )
        ttk.Button(f, text="Add", command=self.log_water).grid(
            row=row, column=2, sticky="w", padx=4, pady=4
        )

        row += 1
        ttk.Label(f, text="Daily goal (oz):").grid(row=row, column=0, sticky="w", padx=4, pady=4)
        self.water_goal_var = tk.StringVar(value=str(get_water_goal()))
        ttk.Entry(f, textvariable=self.water_goal_var, width=10).grid(
            row=row, column=1, sticky="w", padx=4, pady=4
        )
        ttk.Button(f, text="Set goal", command=self.set_water_goal).grid(
            row=row, column=2, sticky="w", padx=4, pady=4
        )

        row += 1
        ttk.Label(f, text="Today:").grid(row=row, column=0, sticky="w", padx=4, pady=4)
        self.water_status_label = ttk.Label(f, text="")
        self.water_status_label.grid(row=row, column=1, columnspan=2, sticky="w", padx=4, pady=4)

        row += 1
        ttk.Label(f, text="Today log:").grid(row=row, column=0, sticky="nw", padx=4, pady=4)
        self.water_log_text = tk.Text(f, height=8, width=50)
        self.water_log_text.grid(row=row, column=1, columnspan=2, sticky="nsew", padx=4, pady=4)

        f.rowconfigure(row, weight=1)
        f.columnconfigure(1, weight=1)

        self.refresh_water_view()

    def log_water(self) -> None:
        try:
            amt = int(self.water_amount_var.get())
        except ValueError:
            messagebox.showerror("Invalid amount", "Please enter a whole number of ounces.")
            return

        data = load_data()
        entries: List[dict] = data["water"]
        entries.append(asdict(WaterEntry(amount_ml=amt, timestamp=now_iso())))
        data["water"] = entries
        save_data(data)
        self.water_amount_var.set("")
        self.refresh_water_view()

    def set_water_goal(self) -> None:
        try:
            goal = int(self.water_goal_var.get())
        except ValueError:
            messagebox.showerror("Invalid goal", "Please enter a whole number for goal.")
            return
        data = load_data()
        data["water_goal"] = goal
        save_data(data)
        self.refresh_water_view()

    def refresh_water_view(self) -> None:
        data = load_data()
        total = get_water_today(data)
        goal = get_water_goal(data)
        self.water_status_label.config(text=progress_bar(total, goal))

        today = dt.date.today().isoformat()
        self.water_log_text.delete("1.0", tk.END)
        for entry in data.get("water", []):
            if entry.get("timestamp", "").split("T")[0] == today:
                self.water_log_text.insert(
                    tk.END,
                    f"{entry['timestamp']}: {entry['amount_ml']} oz\n",
                )

    def reset_today_water(self) -> None:
        data = load_data()
        today = dt.date.today().isoformat()
        data["water"] = [
            e for e in data.get("water", []) if e.get("timestamp", "").split("T")[0] != today
        ]
        save_data(data)
        self.refresh_water_view()
        messagebox.showinfo("Reset", "Today's water log has been reset to 0 oz.")

    # ----- Mood tab -----
    def _build_mood_tab(self) -> None:
        f = self.mood_frame
        ttk.Label(f, text="Mood rating (1–10):").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.mood_rating_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.mood_rating_var, width=5).grid(
            row=0, column=1, sticky="w", padx=4, pady=4
        )

        ttk.Label(f, text="Note (optional):").grid(row=1, column=0, sticky="nw", padx=4, pady=4)
        self.mood_note_text = tk.Text(f, height=4, width=40)
        self.mood_note_text.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=4, pady=4)

        ttk.Button(f, text="Log mood", command=self.log_mood).grid(
            row=2, column=1, sticky="w", padx=4, pady=4
        )

        self.last_mood_label = ttk.Label(f, text="Last mood: (none yet)")
        self.last_mood_label.grid(row=3, column=0, columnspan=3, sticky="w", padx=4, pady=8)

        f.rowconfigure(1, weight=1)
        f.columnconfigure(1, weight=1)

        self.refresh_mood_view()

    def log_mood(self) -> None:
        try:
            rating = int(self.mood_rating_var.get())
        except ValueError:
            messagebox.showerror("Invalid rating", "Please enter a number from 1 to 10.")
            return
        if not 1 <= rating <= 10:
            messagebox.showerror("Invalid rating", "Please enter a number from 1 to 10.")
            return
        note = self.mood_note_text.get("1.0", tk.END).strip()

        data = load_data()
        moods = data.get("moods", [])
        moods.append({"rating": rating, "note": note, "timestamp": now_iso()})
        data["moods"] = moods
        save_data(data)

        self.mood_rating_var.set("")
        self.mood_note_text.delete("1.0", tk.END)
        self.refresh_mood_view()

    def refresh_mood_view(self) -> None:
        data = load_data()
        moods = data.get("moods", [])
        if moods:
            last = moods[-1]
            rating = last.get("rating")
            note = last.get("note", "")
            ts = last.get("timestamp", "")
            text = f"Last mood: {rating}/10"
            if note:
                text += f" – {note}"
            text += f"  ({ts})"
        else:
            text = "Last mood: (none yet)"
        self.last_mood_label.config(text=text)

    # ----- Vyvanse tab -----
    def _build_vyvanse_tab(self) -> None:
        f = self.vyvanse_frame
        self.vy_status_label = ttk.Label(f, text="", justify="left")
        self.vy_status_label.pack(anchor="w", padx=8, pady=8)

        ttk.Button(f, text="Refresh", command=self.refresh_vyvanse_view).pack(
            anchor="w", padx=8, pady=4
        )

        self.refresh_vyvanse_view()

    def refresh_vyvanse_view(self) -> None:
        data = load_data()
        state_dict = data.get("vyvanse")
        if not state_dict:
            self.vy_status_label.config(
                text="No Vyvanse config found.\nUse the CLI 'vyvanse configure' command first."
            )
            return
        state = VyvanseState(**state_dict)
        lines = [
            f"Pills remaining: {state.pill_count}",
            f"Daily dosage:   {state.daily_dosage}",
            f"Refill date:    {state.refill_date}",
        ]

        last_take = get_last_vyvanse_take(data)
        if last_take:
            now = dt.datetime.now()
            hours = (now - last_take).total_seconds() / 3600
            if hours < 0:
                phase = "time anomaly? (log in the future)"
            elif hours < 0.5:
                phase = "onset (0–30 min)"
            elif hours < 3:
                phase = "peak window (~0.5–3 hr after dose)"
            elif hours < 6:
                phase = "plateau (3–6 hr after dose)"
            elif hours < 10:
                phase = "taper (6–10 hr after dose)"
            else:
                phase = "tail / mostly worn off (10+ hr)"
            lines.append(f"Last dose:       {last_take.isoformat(timespec='minutes')}")
            lines.append(f"Estimated phase: {phase}")
        else:
            lines.append("Last dose:       no 'take' logged in vyvanse_log yet.")

        self.vy_status_label.config(text="\n".join(lines))

    # ----- Hemp tab -----
    def _build_hemp_tab(self) -> None:
        f = self.hemp_frame
        ttk.Label(f, text="Amount (mg):").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.hemp_amount_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.hemp_amount_var, width=10).grid(
            row=0, column=1, sticky="w", padx=4, pady=4
        )

        ttk.Label(f, text="Feeling:").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.hemp_feeling_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.hemp_feeling_var, width=30).grid(
            row=1, column=1, columnspan=2, sticky="w", padx=4, pady=4
        )

        ttk.Label(f, text="Outcome/notes:").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.hemp_outcome_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.hemp_outcome_var, width=30).grid(
            row=2, column=1, columnspan=2, sticky="w", padx=4, pady=4
        )

        ttk.Button(f, text="Log hemp", command=self.log_hemp).grid(
            row=3, column=1, sticky="w", padx=4, pady=8
        )

        self.last_hemp_label = ttk.Label(f, text="Last hemp: (none yet)")
        self.last_hemp_label.grid(row=4, column=0, columnspan=3, sticky="w", padx=4, pady=8)

        self.refresh_hemp_view()

    def log_hemp(self) -> None:
        try:
            amount = int(self.hemp_amount_var.get())
        except ValueError:
            messagebox.showerror("Invalid amount", "Please enter a whole number of mg.")
            return

        feeling = self.hemp_feeling_var.get().strip()
        outcome = self.hemp_outcome_var.get().strip()

        data = load_data()
        entries: List[dict] = data.get("hemp", [])
        entries.append(
            asdict(
                HempEntry(
                    amount_mg=amount,
                    feeling=feeling,
                    outcome=outcome,
                    timestamp=now_iso(),
                )
            )
        )
        data["hemp"] = entries
        save_data(data)

        self.hemp_amount_var.set("")
        self.hemp_feeling_var.set("")
        self.hemp_outcome_var.set("")
        self.refresh_hemp_view()

    def refresh_hemp_view(self) -> None:
        data = load_data()
        entries = data.get("hemp", [])
        if entries:
            last = entries[-1]
            text = (
                f"Last hemp: {last.get('amount_mg')} mg"
                f"{' | feeling: ' + last.get('feeling', '') if last.get('feeling') else ''}"
                f"{' | outcome: ' + last.get('outcome', '') if last.get('outcome') else ''}"
                f"  ({last.get('timestamp', '')})"
            )
        else:
            text = "Last hemp: (none yet)"
        self.last_hemp_label.config(text=text)

    # ----- Substance tab -----
    def _build_substance_tab(self) -> None:
        f = self.substance_frame

        ttk.Label(f, text="Substance name:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.sub_name_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.sub_name_var, width=20).grid(
            row=0, column=1, sticky="w", padx=4, pady=4
        )

        ttk.Label(f, text="Amount / units:").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.sub_amount_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.sub_amount_var, width=20).grid(
            row=1, column=1, sticky="w", padx=4, pady=4
        )

        ttk.Label(f, text="Feeling:").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.sub_feeling_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.sub_feeling_var, width=40).grid(
            row=2, column=1, columnspan=2, sticky="w", padx=4, pady=4
        )

        ttk.Label(f, text="Outcome/notes:").grid(row=3, column=0, sticky="w", padx=4, pady=4)
        self.sub_outcome_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.sub_outcome_var, width=40).grid(
            row=3, column=1, columnspan=2, sticky="w", padx=4, pady=4
        )

        ttk.Button(f, text="Log substance", command=self.log_substance).grid(
            row=4, column=1, sticky="w", padx=4, pady=8
        )

        ttk.Label(f, text="Recent substances:").grid(row=5, column=0, sticky="nw", padx=4, pady=4)
        self.sub_recent_text = tk.Text(f, height=8, width=60)
        self.sub_recent_text.grid(row=5, column=1, columnspan=2, sticky="nsew", padx=4, pady=4)

        f.rowconfigure(5, weight=1)
        f.columnconfigure(1, weight=1)

        self.refresh_substance_view()

    def log_substance(self) -> None:
        name = self.sub_name_var.get().strip()
        amount = self.sub_amount_var.get().strip()
        feeling = self.sub_feeling_var.get().strip()
        outcome = self.sub_outcome_var.get().strip()

        if not name:
            messagebox.showerror("Missing name", "Please enter a substance name.")
            return
        if not amount:
            messagebox.showerror("Missing amount", "Please enter an amount / units.")
            return

        data = load_data()
        entries: List[dict] = data.get("substances", [])
        entries.append(
            asdict(
                SubstanceEntry(
                    name=name,
                    amount=amount,
                    feeling=feeling,
                    outcome=outcome,
                    timestamp=now_iso(),
                )
            )
        )
        data["substances"] = entries
        save_data(data)

        self.sub_name_var.set("")
        self.sub_amount_var.set("")
        self.sub_feeling_var.set("")
        self.sub_outcome_var.set("")
        self.refresh_substance_view()

    def refresh_substance_view(self) -> None:
        data = load_data()
        entries = data.get("substances", [])
        self.sub_recent_text.delete("1.0", tk.END)
        for entry in entries[-10:]:
            line = (
                f"{entry.get('timestamp', '')}: {entry.get('name', '')} "
                f"({entry.get('amount', '')})"
            )
            if entry.get("feeling"):
                line += f" | feeling: {entry['feeling']}"
            if entry.get("outcome"):
                line += f" | outcome: {entry['outcome']}"
            self.sub_recent_text.insert(tk.END, line + "\n")

    # ----- Summary tab -----
    def _build_summary_tab(self) -> None:
        f = self.summary_frame
        self.summary_text = tk.Text(f, height=20, width=70)
        self.summary_text.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Button(f, text="Refresh summary", command=self.refresh_summary).pack(
            pady=(0, 6)
        )

    def refresh_summary(self) -> None:
        data = load_data()
        now = dt.datetime.now()

        lines = []
        lines.append("ChaosCatcher Summary")
        lines.append("=" * 24)
        lines.append(f"Now: {now.isoformat(timespec='minutes')}")
        lines.append("")

        # Vyvanse
        lines.append("[VYVANSE]")
        state_dict = data.get("vyvanse")
        if state_dict:
            state = VyvanseState(**state_dict)
            lines.append(f"Pills remaining: {state.pill_count}")
            lines.append(f"Daily dosage:   {state.daily_dosage}")
            lines.append(f"Refill date:    {state.refill_date}")

            last_take = get_last_vyvanse_take(data)
            if last_take:
                hours = (now - last_take).total_seconds() / 3600
                if hours < 0:
                    phase = "time anomaly? (log in the future)"
                elif hours < 0.5:
                    phase = "onset (0–30 min)"
                elif hours < 3:
                    phase = "peak window (~0.5–3 hr after dose)"
                elif hours < 6:
                    phase = "plateau (3–6 hr after dose)"
                elif hours < 10:
                    phase = "taper (6–10 hr after dose)"
                else:
                    phase = "tail / mostly worn off (10+ hr)"
                lines.append(f"Last dose:       {last_take.isoformat(timespec='minutes')}")
                lines.append(f"Estimated phase: {phase}")
            else:
                lines.append("Last dose:       no 'take' logged in vyvanse_log yet.")
        else:
            lines.append("No Vyvanse config found. Use CLI 'vyvanse configure' first.")
        lines.append("")

        # Water
        lines.append("[WATER]")
        goal = get_water_goal(data)
        total_today = get_water_today(data)
        lines.append(f"Goal:  {goal} oz")
        lines.append(progress_bar(total_today, goal))
        lines.append("")

        # Mood
        lines.append("[MOOD]")
        moods = data.get("moods", [])
        if moods:
            last = moods[-1]
            rating = last.get("rating")
            note = last.get("note", "")
            ts = last.get("timestamp", "")
            line = f"Last mood: {rating}/10"
            if note:
                line += f" – {note}"
            line += f"  ({ts})"
            lines.append(line)
        else:
            lines.append("No mood entries yet. Log one from the Mood tab or CLI.")
        lines.append("")

        # Hemp
        lines.append("[HEMP]")
        hemp_entries = data.get("hemp", [])
        if hemp_entries:
            last = hemp_entries[-1]
            line = f"Last hemp: {last.get('amount_mg')} mg"
            if last.get("feeling"):
                line += f" | feeling: {last['feeling']}"
            if last.get("outcome"):
                line += f" | outcome: {last['outcome']}"
            line += f"  ({last.get('timestamp', '')})"
            lines.append(line)
        else:
            lines.append("No hemp entries yet.")
        lines.append("")

        # Substance
        lines.append("[SUBSTANCES]")
        subs = data.get("substances", [])
        if subs:
            for entry in subs[-5:]:
                line = (
                    f"{entry.get('timestamp', '')}: {entry.get('name', '')} "
                    f"({entry.get('amount', '')})"
                )
                if entry.get("feeling"):
                    line += f" | feeling: {entry['feeling']}"
                if entry.get("outcome"):
                    line += f" | outcome: {entry['outcome']}"
                lines.append(line)
        else:
            lines.append("No substances logged yet.")
        lines.append("")

        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "\n".join(lines))


def main() -> None:
    app = ChaosCatcherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
