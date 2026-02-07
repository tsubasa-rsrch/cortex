#!/usr/bin/env python3
"""
Cortex Live Dashboard: Real-Time Perception Monitor
====================================================
Watches tsubasa-daemon event log in real-time and processes
each new event through the Cortex perception pipeline.

Shows a live terminal dashboard with:
- Current perception state (habituated vs conscious)
- Circadian rhythm info
- Running stats (filtered %, orienting count)
- Color-coded event stream

Usage:
    python examples/live_dashboard.py
    python examples/live_dashboard.py --log /path/to/event_log.jsonl
"""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cortex import CortexConfig, HabituationFilter, CircadianRhythm, DecisionEngine, NotificationQueue
from cortex.sources.base import Event

# ANSI color codes
_USE_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

def _bold(t): return _c("1", t)
def _dim(t): return _c("2", t)
def _green(t): return _c("32", t)
def _red(t): return _c("31", t)
def _yellow(t): return _c("33", t)
def _cyan(t): return _c("36", t)
def _magenta(t): return _c("35", t)
def _white(t): return _c("97", t)
def _bg_green(t): return _c("42;30", t)
def _bg_red(t): return _c("41;97", t)
def _bg_yellow(t): return _c("43;30", t)


def clear_screen():
    if _USE_COLOR:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def draw_header(stats):
    """Draw the dashboard header with running stats."""
    now = datetime.now().strftime("%H:%M:%S")
    total = stats["total"]
    passed = stats["passed"]
    filtered = stats["filtered"]
    orienting = stats["orienting"]
    reduction = (filtered / total * 100) if total > 0 else 0

    lines = []
    lines.append(_cyan("=" * 62))
    lines.append(_bold(_cyan(f"  Cortex Live Dashboard  |  {now}  |  watching...")))
    lines.append(_cyan("=" * 62))
    lines.append("")
    lines.append(f"  {_bold('Events:')} {_white(str(total))}  "
                 f"{_bold('Conscious:')} {_green(str(passed))}  "
                 f"{_bold('Filtered:')} {_red(str(filtered))}  "
                 f"{_bold('Orienting:')} {_yellow(str(orienting))}")

    if total > 0:
        bar_total = 40
        bar_passed = int(passed / total * bar_total)
        bar_filtered = bar_total - bar_passed
        bar = _green("\u2588" * bar_passed) + _red("\u2588" * bar_filtered)
        lines.append(f"  [{bar}] {_bg_green(f' {reduction:.0f}% filtered ')}")
    lines.append("")
    lines.append(_dim("-" * 62))
    return "\n".join(lines)


def format_event(event, should_notify, reason, is_orienting):
    """Format a single event for display."""
    ts = event.get("timestamp", "")[:19]
    etype = event.get("type", "?")
    meta = event.get("metadata", {})

    if etype == "motion":
        camera = meta.get("camera", "?")
        diff = meta.get("diff", 0)

        if not should_notify:
            icon = _dim("[---]")
            detail = _dim(f"{camera} diff={diff:.1f} ({reason})")
        elif is_orienting:
            icon = _bg_yellow(" ! ")
            detail = _yellow(f"{camera} diff={diff:.1f} ORIENTING")
        elif diff >= 30:
            icon = _bg_red(" ! ")
            detail = _red(f"{camera} diff={diff:.1f} URGENT")
        else:
            icon = _green("[>>>]")
            detail = _green(f"{camera} diff={diff:.1f}")

        return f"  {_dim(ts[11:])} {icon} {detail}"

    elif etype == "telegram":
        content = event.get("content", "")[:50]
        return f"  {_dim(ts[11:])} {_cyan('[TG]')} {_cyan(content)}"

    else:
        content = event.get("content", "")[:50]
        return f"  {_dim(ts[11:])} {_magenta(f'[{etype}]')} {content}"


def tail_file(path, from_end=0):
    """Yield new lines as they appear in a file."""
    with open(path) as f:
        # Seek to near end if from_end > 0
        if from_end > 0:
            lines = f.readlines()
            start = max(0, len(lines) - from_end)
            for line in lines[start:]:
                yield line.strip()
        else:
            f.seek(0, 2)  # Seek to end

        while True:
            line = f.readline()
            if line:
                yield line.strip()
            else:
                time.sleep(0.5)


def main():
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description="Cortex Live Dashboard")
    parser.add_argument("--log", type=str, help="Path to event_log.jsonl")
    parser.add_argument("--history", type=int, default=20,
                        help="Show last N events at start (default: 20)")
    parser.add_argument("--compact", action="store_true",
                        help="Compact mode (no screen clearing)")
    args = parser.parse_args()

    # Find event log
    log_path = args.log
    if log_path is None:
        candidates = [
            Path.home() / ".tsubasa-daemon" / "memory" / "event_log.jsonl",
        ]
        for p in candidates:
            if p.exists():
                log_path = str(p)
                break

    if not log_path or not Path(log_path).exists():
        print("No event log found. Provide --log path.")
        sys.exit(1)

    # Initialize Cortex modules
    tmp = Path(tempfile.mkdtemp())
    hab = HabituationFilter(cooldown=30.0, base_threshold=15.0, orienting_mult=2.0)
    circadian = CircadianRhythm()
    engine = DecisionEngine()
    notifications = NotificationQueue(CortexConfig(data_dir=tmp))

    stats = {"total": 0, "passed": 0, "filtered": 0, "orienting": 0}
    event_buffer = []
    max_buffer = 30  # Keep last 30 events on screen

    print(_bold(_cyan("Starting Cortex Live Dashboard...")))
    print(f"  Watching: {_white(log_path)}")
    print(f"  Press Ctrl+C to stop")
    print()

    try:
        for line in tail_file(log_path, from_end=args.history):
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = event.get("type", "")

            # Process through Cortex
            should = True
            reason = ""
            is_orienting = False

            if etype == "motion":
                meta = event.get("metadata", {})
                diff = meta.get("diff", 0)
                camera = meta.get("camera", "unknown")
                event_type = f"motion_{camera}"

                should, reason = hab.should_notify(event_type, diff)
                is_orienting = "rienting" in reason

                stats["total"] += 1
                if should:
                    stats["passed"] += 1
                    if is_orienting:
                        stats["orienting"] += 1
                else:
                    stats["filtered"] += 1

            # Format event
            formatted = format_event(event, should, reason, is_orienting)
            event_buffer.append(formatted)
            if len(event_buffer) > max_buffer:
                event_buffer.pop(0)

            # Draw
            if not args.compact:
                clear_screen()
                print(draw_header(stats))
                for line in event_buffer:
                    print(line)
                sys.stdout.flush()
            else:
                # Compact mode: just print each event
                print(formatted, flush=True)
                # Print stats every 50 events
                if stats["total"] % 50 == 0 and stats["total"] > 0:
                    r = stats["filtered"] / stats["total"] * 100
                    t = stats["total"]
                    print(f"  {_dim(f'--- {t} events, {r:.0f}% filtered ---')}", flush=True)

    except KeyboardInterrupt:
        print()
        print(_cyan("=" * 62))
        print(_bold(_cyan("  Dashboard stopped.")))
        total = stats["total"]
        if total > 0:
            r = stats["filtered"] / total * 100
            print(f"  {total} events processed, {_bg_green(f' {r:.0f}% filtered ')}")
        print(_cyan("=" * 62))


if __name__ == "__main__":
    main()
