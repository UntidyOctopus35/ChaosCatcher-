# ChaosCatcher

A terminal-friendly self-care suite covering focus tracking, mood logging, hydration, Vyvanse pills, and substance journaling. Data is stored in JSON (default: `~/.chaoscatcher.json`) and can be redirected with `--data path/to/file.json`.

## Installation
Requires Python 3.9+. No external dependencies.

```bash
python chaoscatcher.py --help
```

## Focus to-do + timer
```bash
python chaoscatcher.py focus add "Write report" 25 --timer 25  # run timer and log minutes
python chaoscatcher.py focus summary --limit 5                  # show recent sessions
```

## Mood tracker + graph
```bash
python chaoscatcher.py mood log 7 --note "Calm morning"
python chaoscatcher.py mood graph --limit 10
```

## Water intake
```bash
python chaoscatcher.py water log 350   # log milliliters
python chaoscatcher.py water today     # sum of today
```

## Vyvanse pill counter with projected refill date
```bash
python chaoscatcher.py vyvanse configure --pill-count 30 --daily-dosage 1
python chaoscatcher.py vyvanse take 1
python chaoscatcher.py vyvanse refill 30
python chaoscatcher.py vyvanse status
```
The refill date recalculates automatically based on remaining pills and daily dosage.

## Hemp tracker
```bash
python chaoscatcher.py hemp 15 --feeling "relaxed" --outcome "slept well"
```

## Other substances
```bash
python chaoscatcher.py substance caffeine "200mg" --feeling "alert" --outcome "slight jitters"
```

## Tips
- All timestamps are stored in local time (`YYYY-MM-DDTHH:MM`).
- Use `CTRL+C` to stop the focus timer early; the elapsed minutes will be recorded.
