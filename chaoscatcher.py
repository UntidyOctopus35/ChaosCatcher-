#!/usr/bin/env python3
"""ChaosCatcher self-care suite CLI.

Features
- Focus to-do tracker with optional countdown timer and time spent logging.
- Mood tracker with ASCII trend graph.
- Water intake tracker.
- Vyvanse pill counter with automatic refill date projection.
- Hemp tracker capturing amount, feeling, and outcome.
- Generic substance tracker for other substances.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from typing import List, Optional

DATA_PATH = os.environ.get(
    "CHAOSCATCHER_DATA", os.path.join(os.path.expanduser("~"), ".chaoscatcher.json")
)


# --------- models ---------
@dataclass
class FocusSession:
    task: str
    minutes: int
    timestamp: str


@dataclass
class MoodEntry:
    rating: int
    note: str
    timestamp: str


@dataclass
class WaterEntry:
    amount_ml: int   # treated as oz in practice
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


# --------- helpers ---------
def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="minutes")


def load_data() -> dict:
    if not os.path.exists(DATA_PATH):
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
    if "water_goal" not in data:
        data["water_goal"] = 64
    if "water" not in data:
        data["water"] = []
    return data


def save_data(data: dict) -> None:
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def ensure_data_dir():
    os.makedirs(os.path.dirname(DATA_PATH) or ".", exist_ok=True)


def print_boxed(text: str) -> None:
    border = "=" * len(text)
    print(border)
    print(text)
    print(border)


# --------- focus ---------
def handle_focus(args: argparse.Namespace) -> None:
    data = load_data()
    sessions: List[dict] = data["focus_sessions"]
    if args.command == "add":
        minutes = args.minutes
        if args.timer:
            minutes = run_timer(args.timer)
        sessions.append(
            asdict(
                FocusSession(
                    task=args.task,
                    minutes=minutes,
                    timestamp=now_iso(),
                )
            )
        )
        save_data(data)
        print(f"Logged {minutes} minutes on '{args.task}'. Data saved to {DATA_PATH}.")
    elif args.command == "summary":
        if not sessions:
            print("No focus sessions yet. Add one with 'focus add'.")
            return
        total = sum(s["minutes"] for s in sessions)
        print_boxed(f"Total focus minutes: {total}")
        if args.limit:
            recent = sessions[-args.limit :]
        else:
            recent = sessions
        for sess in recent:
            print(f"{sess['timestamp']}: {sess['task']} - {sess['minutes']} minutes")


def run_timer(minutes: int) -> int:
    print(f"Starting timer for {minutes} minutes. Press Ctrl+C to stop early.")
    start = time.time()
    try:
        for remaining in range(minutes * 60, 0, -1):
            mins, secs = divmod(remaining, 60)
            sys.stdout.write(f"\rTime left: {mins:02d}:{secs:02d}")
            sys.stdout.flush()
            time.sleep(1)
        print("\nTimer finished!")
        return minutes
    except KeyboardInterrupt:
        elapsed_minutes = int((time.time() - start) // 60)
        print(f"\nTimer stopped early. Logged {elapsed_minutes} minutes.")
        return elapsed_minutes


# --------- mood ---------
def handle_mood(args: argparse.Namespace) -> None:
    data = load_data()
    entries: List[dict] = data["moods"]
    if args.command == "log":
        entry = asdict(
            MoodEntry(
                rating=args.rating,
                note=args.note or "",
                timestamp=now_iso(),
            )
        )
        entries.append(entry)
        save_data(data)
        print(
            f"Mood logged: {args.rating}/10"
            f"{' - ' + args.note if args.note else ''}."
        )
    elif args.command == "graph":
        if not entries:
            print("No mood entries yet. Add one with 'mood log'.")
            return
        print_boxed("Mood trend (latest last)")
        graph_moods(entries[-args.limit :] if args.limit else entries)


def graph_moods(entries: List[dict]) -> None:
    ratings = [e["rating"] for e in entries]
    min_r, max_r = min(ratings), max(ratings)
    span = max(max_r - min_r, 1)
    scaled = [int(((r - min_r) / span) * 10) for r in ratings]
    for idx, entry in enumerate(entries, 1):
        bar = "▁▂▃▄▅▆▇█"[min(7, scaled[idx - 1] // 2)]
        print(
            f"{idx:>3} {bar} {entry['rating']}/10 {entry['note']} "
            f"({entry['timestamp']})"
        )


# --------- water helpers ---------
def get_water_goal(data: Optional[dict] = None) -> int:
    if data is None:
        data = load_data()
    return data.get("water_goal", 64)


def set_water_goal(goal: int) -> None:
    data = load_data()
    data["water_goal"] = goal
    save_data(data)
    print(f"Water goal set to {goal} oz per day.")


def get_water_today(data: Optional[dict] = None) -> int:
    if data is None:
        data = load_data()
    today = dt.date.today().isoformat()
    total = 0
    for entry in data["water"]:
        ts = entry["timestamp"]
        date = ts.split("T")[0]
        if date == today:
            total += entry["amount_ml"]  # treated as oz
    return total


def progress_bar(current: int, total: int, length: int = 20) -> str:
    if total <= 0:
        total = 1
    filled = int((current / total) * length)
    filled = max(0, min(length, filled))
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {current}/{total} oz"


def water_graph_7() -> None:
    data = load_data()
    entries: List[dict] = data["water"]

    if not entries:
        print("No water entries yet. Log some with 'water log'.")
        return

    goal = data.get("water_goal", 64)

    # aggregate totals per date
    totals = {}
    for entry in entries:
        date = entry["timestamp"].split("T")[0]
        totals[date] = totals.get(date, 0) + entry["amount_ml"]

    today = dt.date.today()
    print_boxed(f"Hydration – last 7 days (goal: {goal} oz)")

    for i in range(6, -1, -1):
        day = today - dt.timedelta(days=i)
        key = day.isoformat()
        total = totals.get(key, 0)
        blocks = int(round(total / 8))  # 1 block = 8 oz
        bar = "█" * blocks if blocks > 0 else "·"
        print(f"{day.strftime('%a')}: {bar}  ({total} oz)")


# --------- water ---------
def handle_water(args: argparse.Namespace) -> None:
    data = load_data()
    entries: List[dict] = data["water"]

    if args.command == "log":
        # Keep field name amount_ml, treat it as ounces internally.
        entries.append(
            asdict(
                WaterEntry(
                    amount_ml=args.amount,
                    timestamp=now_iso(),
                )
            )
        )
        save_data(data)
        print(f"Logged {args.amount} oz of water.")

    elif args.command == "today":
        total = get_water_today(data)
        print_boxed(f"Today's water: {total} oz")
        today = dt.date.today().isoformat()
        for entry in entries:
            if entry["timestamp"].split("T")[0] == today:
                print(f"{entry['timestamp']}: {entry['amount_ml']} oz")

    elif args.command == "goal":
        set_water_goal(args.amount)

    elif args.command == "status":
        total = get_water_today(data)
        goal = get_water_goal(data)
        print_boxed("Water status")
        print(f"Goal:  {goal} oz")
        print(progress_bar(total, goal))

    elif args.command == "graph":
        water_graph_7()

    elif args.command == "reset":
        today = dt.date.today().isoformat()
        data["water"] = [
            entry
            for entry in entries
            if entry["timestamp"].split("T")[0] != today
        ]
        save_data(data)
        print("Today's water log has been reset to 0 oz.")

    else:
        print("Use one of: log, today, goal, status, graph, reset.")


# --------- vyvanse ---------
def handle_vyvanse(args: argparse.Namespace) -> None:
    data = load_data()
    state = VyvanseState(
        **data.get(
            "vyvanse",
            VyvanseState(0, 1, now_iso().split("T")[0]).__dict__,
        )
    )
    log: List[dict] = data["vyvanse_log"]

    if args.command == "configure":
        if args.pill_count is not None:
            state.pill_count = args.pill_count
        if args.daily_dosage is not None:
            state.daily_dosage = args.daily_dosage
        if args.refill_date:
            state.refill_date = args.refill_date
        save_vyvanse(data, state, log, reason="configuration updated")
        print_vyvanse(state)
    elif args.command == "take":
        state.pill_count -= args.amount
        save_vyvanse(data, state, log, reason=f"took {args.amount}")
        print_vyvanse(state)
    elif args.command == "refill":
        state.pill_count += args.amount
        state.refill_date = predict_refill_date(state)
        save_vyvanse(data, state, log, reason=f"refilled +{args.amount}")
        print_vyvanse(state)
    elif args.command == "status":
        print_vyvanse(state)


def predict_refill_date(state: VyvanseState) -> str:
    if state.daily_dosage <= 0:
        return state.refill_date
    days_left = max(state.pill_count, 0) // state.daily_dosage
    return (dt.date.today() + dt.timedelta(days=days_left)).isoformat()


def save_vyvanse(data: dict, state: VyvanseState, log: List[dict], reason: str) -> None:
    state.refill_date = predict_refill_date(state)
    log.append(
        asdict(
            VyvanseLog(
                change=state.daily_dosage,
                reason=reason,
                timestamp=now_iso(),
            )
        )
    )
    data["vyvanse"] = asdict(state)
    data["vyvanse_log"] = log
    save_data(data)


def print_vyvanse(state: VyvanseState) -> None:
    warning = "" if state.pill_count > 0 else " ⚠️ Refill needed!"
    print_boxed("Vyvanse status")
    print(
        f"Pills remaining: {state.pill_count}\n"
        f"Daily dosage: {state.daily_dosage}\n"
        f"Projected refill date: {state.refill_date}{warning}"
    )


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


# --------- summary ---------
def handle_summary(args: argparse.Namespace) -> None:
    data = load_data()
    now = dt.datetime.now()

    print_boxed("ChaosCatcher Summary")

    # --- Vyvanse section ---
    print("\n[VYVANSE]")
    state_dict = data.get("vyvanse")
    if state_dict:
        state = VyvanseState(**state_dict)
        print(f"Pills remaining: {state.pill_count}")
        print(f"Daily dosage:   {state.daily_dosage}")
        print(f"Refill date:    {state.refill_date}")

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

            print(f"Last dose:       {last_take.isoformat(timespec='minutes')}")
            print(f"Estimated phase: {phase}")
        else:
            print("Last dose:       no 'take' logged in vyvanse_log yet.")
    else:
        print("No Vyvanse config found. Use 'vyvanse configure' first.")

    # --- Water section ---
    print("\n[WATER]")
    goal = get_water_goal(data)
    total_today = get_water_today(data)
    print(f"Goal:  {goal} oz")
    print(progress_bar(total_today, goal))

    # --- Mood section ---
    print("\n[MOOD]")
    moods = data.get("moods", [])
    if moods:
        last = moods[-1]
        rating = last.get("rating")
        note = last.get("note", "")
        ts = last.get("timestamp", "")
        print(f"Last mood: {rating}/10{' - ' + note if note else ''}")
        print(f"Logged at: {ts}")
    else:
        print("No mood entries yet. Log one with 'mood log'.")


# --------- hemp ---------
def handle_hemp(args: argparse.Namespace) -> None:
    data = load_data()
    entries: List[dict] = data["hemp"]
    entries.append(
        asdict(
            HempEntry(
                amount_mg=args.amount,
                feeling=args.feeling or "",
                outcome=args.outcome or "",
                timestamp=now_iso(),
            )
        )
    )
    save_data(data)
    print(
        f"Hemp logged: {args.amount} mg"
        f"{' | feeling: ' + args.feeling if args.feeling else ''}"
        f"{' | outcome: ' + args.outcome if args.outcome else ''}"
    )


# --------- substances ---------
def handle_substance(args: argparse.Namespace) -> None:
    data = load_data()
    entries: List[dict] = data["substances"]
    entries.append(
        asdict(
            SubstanceEntry(
                name=args.name,
                amount=args.amount,
                feeling=args.feeling or "",
                outcome=args.outcome or "",
                timestamp=now_iso(),
            )
        )
    )
    save_data(data)
    print(f"Logged {args.name} ({args.amount}).")


# --------- CLI ---------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ChaosCatcher self-care suite")
    parser.add_argument(
        "--data",
        default=DATA_PATH,
        help="Custom path for data JSON (default: ~/.chaoscatcher.json)",
    )

    sub = parser.add_subparsers(dest="section")

    # Focus
    focus = sub.add_parser("focus", help="Track focus sessions")
    focus_sub = focus.add_subparsers(dest="command")
    focus_add = focus_sub.add_parser("add", help="Add a focus session")
    focus_add.add_argument("task", help="Task name")
    focus_add.add_argument("minutes", type=int, help="Minutes spent")
    focus_add.add_argument(
        "--timer",
        type=int,
        help="Start a countdown timer for given minutes",
    )
    focus_add.set_defaults(func=handle_focus)

    focus_summary = focus_sub.add_parser("summary", help="Show focus summary")
    focus_summary.add_argument(
        "--limit",
        type=int,
        help="Limit to most recent N sessions",
    )
    focus_summary.set_defaults(func=handle_focus)

    # Mood
    mood = sub.add_parser("mood", help="Log moods and view graph")
    mood_sub = mood.add_subparsers(dest="command")
    mood_log = mood_sub.add_parser("log", help="Log a mood entry")
    mood_log.add_argument(
        "rating",
        type=int,
        choices=range(1, 11),
        help="Mood rating 1-10",
    )
    mood_log.add_argument("--note", help="Optional mood note")
    mood_log.set_defaults(func=handle_mood)

    mood_graph = mood_sub.add_parser("graph", help="Show ASCII mood graph")
    mood_graph.add_argument(
        "--limit",
        type=int,
        help="Limit to most recent N entries",
    )
    mood_graph.set_defaults(func=handle_mood)

    # Water
    water = sub.add_parser("water", help="Track water intake")
    water_sub = water.add_subparsers(dest="command")

    water_log = water_sub.add_parser("log", help="Log water intake in oz")
    water_log.add_argument("amount", type=int, help="Amount in oz")
    water_log.set_defaults(func=handle_water)

    water_today = water_sub.add_parser("today", help="Show today's water total")
    water_today.set_defaults(func=handle_water)

    water_goal = water_sub.add_parser("goal", help="Set daily water goal in oz")
    water_goal.add_argument("amount", type=int, help="Goal in oz")
    water_goal.set_defaults(func=handle_water)

    water_status = water_sub.add_parser(
        "status",
        help="Show today's water vs goal",
    )
    water_status.set_defaults(func=handle_water)

    water_graph_cmd = water_sub.add_parser(
        "graph",
        help="Show last 7 days water graph",
    )
    water_graph_cmd.set_defaults(func=handle_water)

    water_reset = water_sub.add_parser(
        "reset",
        help="Reset today's water to 0 oz",
    )
    water_reset.set_defaults(func=handle_water)

    # Vyvanse
    vyvanse = sub.add_parser("vyvanse", help="Manage Vyvanse pills")
    vyvanse_sub = vyvanse.add_subparsers(dest="command")

    vy_conf = vyvanse_sub.add_parser("configure", help="Set counts and refill date")
    vy_conf.add_argument("--pill-count", type=int, help="Current pill count")
    vy_conf.add_argument("--daily-dosage", type=int, help="Pills taken per day")
    vy_conf.add_argument(
        "--refill-date",
        help="Next refill date (YYYY-MM-DD)",
    )
    vy_conf.set_defaults(func=handle_vyvanse)

    vy_take = vyvanse_sub.add_parser("take", help="Log taking pills")
    vy_take.add_argument("amount", type=int, help="Number of pills taken")
    vy_take.set_defaults(func=handle_vyvanse)

    vy_refill = vyvanse_sub.add_parser("refill", help="Add refill to stock")
    vy_refill.add_argument("amount", type=int, help="Number of pills added")
    vy_refill.set_defaults(func=handle_vyvanse)

    vy_status = vyvanse_sub.add_parser("status", help="Show Vyvanse status")
    vy_status.set_defaults(func=handle_vyvanse)

    # Summary
    summary = sub.add_parser(
        "summary",
        help="Show daily ChaosCatcher dashboard",
    )
    summary.set_defaults(func=handle_summary)

    # Hemp
    hemp = sub.add_parser("hemp", help="Log hemp usage")
    hemp.add_argument("amount", type=int, help="Amount in mg")
    hemp.add_argument("--feeling", help="Immediate feeling")
    hemp.add_argument("--outcome", help="Outcome or notes")
    hemp.set_defaults(func=handle_hemp)

    # Substances
    subst = sub.add_parser("substance", help="Log other substances")
    subst.add_argument("name", help="Substance name")
    subst.add_argument("amount", help="Amount/units consumed")
    subst.add_argument("--feeling", help="Feeling after use")
    subst.add_argument("--outcome", help="Outcome or notes")
    subst.set_defaults(func=handle_substance)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    global DATA_PATH
    DATA_PATH = args.data
    ensure_data_dir()

    if not args.section:
        parser.print_help()
        return
    if not hasattr(args, "func"):
        parser.error("Please provide a subcommand.")
        return
    args.func(args)


if __name__ == "__main__":
    main()
