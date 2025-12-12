#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import datetime as dt

from winotify import Notification, audio  # Windows notifications

import chaoscatcher as cc  # your existing CLI logic


# ----------------- notifications -----------------
def send_hydrate_notification(amount: int, total_today: int) -> None:
    """
    Show a Windows notification reminding you that you logged water.
    """
    toast = Notification(
        app_id="ChaosCatcher",
        title="Hydrate, creature",
        msg=f"You just logged {amount} oz. Total today: {total_today} oz.",
        duration="short",  # 'short' or 'long'
    )
    toast.set_audio(audio.Default, loop=False)
    toast.show()


def send_hydrate_reminder(total_today: int, goal: int) -> None:
    """
    Show a periodic hydration reminder if you're below goal.
    """
    remaining = max(goal - total_today, 0)
    msg = (
        f"Total today: {total_today} oz. "
        f"{'Goal reached! 🎉' if remaining == 0 else f'{remaining} oz to go.'}"
    )

    toast = Notification(
        app_id="ChaosCatcher",
        title="Hydrate, creature (scheduled)",
        msg=msg,
        duration="short",
    )
    toast.set_audio(audio.Default, loop=False)
    toast.show()


def schedule_hydration_reminders(root: tk.Tk, minutes: int = 60) -> None:
    """
    Schedule periodic hydration reminders every `minutes`.
    Only reminds you if you're under your water goal.
    """
    interval_ms = minutes * 60 * 1000  # minutes → milliseconds

    def _reminder():
        data = cc.load_data()
        total_today = cc.get_water_today(data)
        goal = cc.get_water_goal(data)

        # Only nag if you're below goal
        if total_today < goal:
            try:
                send_hydrate_reminder(total_today, goal)
            except Exception as e:
                print(f"[hydrate reminder error] {e}")

        # schedule the next reminder
        root.after(interval_ms, _reminder)

    # Kick off the first reminder cycle
    root.after(interval_ms, _reminder)


# ----------------- summary text -----------------
def build_summary_text() -> str:
    data = cc.load_data()
    now = dt.datetime.now()
    lines = []

    lines.append("ChaosCatcher Summary")
    lines.append("=" * len(lines[0]))
    lines.append("")

    # --- Vyvanse section ---
    lines.append("[VYVANSE]")
    state_dict = data.get("vyvanse")
    if state_dict:
        state = cc.VyvanseState(**state_dict)
        lines.append(f"Pills remaining: {state.pill_count}")
        lines.append(f"Daily dosage:   {state.daily_dosage}")
        lines.append(f"Refill date:    {state.refill_date}")

        last_take = cc.get_last_vyvanse_take(data)
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
            lines.append("Last dose:       no 'take' logged yet.")
    else:
        lines.append("No Vyvanse config found. Use CLI 'vyvanse configure'.")

    # --- Water section ---
    lines.append("")
    lines.append("[WATER]")
    goal = cc.get_water_goal(data)
    total_today = cc.get_water_today(data)
    bar = cc.progress_bar(total_today, goal)
    lines.append(f"Goal:  {goal} oz")
    lines.append(bar)

    # --- Mood section ---
    lines.append("")
    lines.append("[MOOD]")
    moods = data.get("moods", [])
    if moods:
        last = moods[-1]
        rating = last.get("rating")
        note = last.get("note", "")
        ts = last.get("timestamp", "")
        line = f"Last mood: {rating}/10"
        if note:
            line += f" - {note}"
        lines.append(line)
        lines.append(f"Logged at: {ts}")
    else:
        lines.append("No mood entries yet. Use CLI 'mood log' to add one.")

    return "\n".join(lines)


# ----------------- GUI actions -----------------
def refresh_summary(text_widget: tk.Text, status_label: tk.Label) -> None:
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    text_widget.insert(tk.END, build_summary_text())
    text_widget.config(state="disabled")
    status_label.config(text=f"Last refreshed: {dt.datetime.now().strftime('%H:%M:%S')}")


def log_water(amount: int, text_widget: tk.Text, status_label: tk.Label) -> None:
    data = cc.load_data()
    entries = data["water"]
    entries.append(
        cc.asdict(cc.WaterEntry(amount_ml=amount, timestamp=cc.now_iso()))
    )
    cc.save_data(data)

    total_today = cc.get_water_today(data)
    status_label.config(text=f"Logged {amount} oz of water. Total today: {total_today} oz")

    # 🔔 Windows notification using winotify
    try:
        send_hydrate_notification(amount, total_today)
    except Exception as e:
        # Fail silently if notifications explode; app still works
        print(f"[notify error] {e}")

    refresh_summary(text_widget, status_label)


def reset_water_today(text_widget: tk.Text, status_label: tk.Label) -> None:
    """
    Delete today's water entries and reset progress bar back to 0 for today.
    """
    data = cc.load_data()
    today = dt.date.today().isoformat()

    data["water"] = [
        entry
        for entry in data.get("water", [])
        if entry["timestamp"].split("T")[0] != today
    ]
    cc.save_data(data)

    status_label.config(text="Reset today's water to 0 oz.")
    refresh_summary(text_widget, status_label)


# ----------------- main window -----------------
def main():
    root = tk.Tk()
    root.title("ChaosCatcher Dashboard")

    # Window layout
    root.geometry("700x500")

    # Summary text area
    text = tk.Text(root, wrap="word", font=("Consolas", 11))
    text.pack(fill="both", expand=True, padx=10, pady=(10, 0))

    # Controls frame
    controls = ttk.Frame(root)
    controls.pack(fill="x", padx=10, pady=10)

    status = tk.Label(root, text="", anchor="w")
    status.pack(fill="x", padx=10, pady=(0, 10))

    # Buttons
    refresh_btn = ttk.Button(
        controls,
        text="Refresh Summary",
        command=lambda: refresh_summary(text, status),
    )
    refresh_btn.pack(side="left")

    ttk.Label(controls, text="Quick water log:").pack(side="left", padx=(15, 5))

    for amt in (8, 12, 16):
        btn = ttk.Button(
            controls,
            text=f"{amt} oz",
            command=lambda a=amt: log_water(a, text, status),
        )
        btn.pack(side="left", padx=2)

    # 🔁 Reset-today button
    reset_btn = ttk.Button(
        controls,
        text="Reset Today",
        command=lambda: reset_water_today(text, status),
    )
    reset_btn.pack(side="left", padx=(15, 0))

    # Initial load
    refresh_summary(text, status)

    # Optional: turn on scheduled reminders every 60 minutes
    # schedule_hydration_reminders(root, minutes=60)

    root.mainloop()


if __name__ == "__main__":
    main()
