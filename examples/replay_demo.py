#!/usr/bin/env python3
"""
Cortex Replay Demo: Real-World Data Pipeline
=============================================
Replays 1,155 real events from a 22-hour daemon session through
the Cortex perception pipeline to demonstrate cognitive filtering.

Data source: tsubasa-daemon motion detection + Telegram messages
  - 944 motion events from bedroom/kitchen cameras
  - 211 Telegram messages (content sanitized for privacy)

This is NOT synthetic data. This is what happens when you give
an AI agent real eyes (cameras) and let it watch the world.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# ANSI color codes (disable if not a TTY)
_USE_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

def _c(code: str, text: str) -> str:
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
def _bg_cyan(t): return _c("46;30", t)

from cortex import CortexConfig, HabituationFilter, CircadianRhythm, DecisionEngine, NotificationQueue
from cortex.sources.base import Event


def load_events(path: str = None) -> list:
    """Load real events from daemon event log."""
    if path is None:
        candidates = [
            Path.home() / ".tsubasa-daemon" / "memory" / "event_log.jsonl",
            Path(__file__).parent / "sample_events.jsonl",
            Path(__file__).parent.parent / "cortex" / "data" / "sample_events.jsonl",
        ]
        for p in candidates:
            if p.exists():
                path = str(p)
                break

    if not path or not Path(path).exists():
        print("No event log found. Using synthetic demo data.")
        return _synthetic_events()

    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def _synthetic_events() -> list:
    """Fallback synthetic data for demo without real log."""
    import random
    events = []
    base = datetime(2026, 2, 6, 16, 0, 0)
    cameras = ["bedroom", "kitchen"]
    for i in range(100):
        ts = base.timestamp() + i * 90
        diff = random.gauss(18, 8)
        if diff < 5:
            diff = 5
        events.append({
            "timestamp": datetime.fromtimestamp(ts).isoformat(),
            "type": "motion",
            "content": f"{random.choice(cameras)}: diff={diff:.1f}",
            "metadata": {
                "camera": random.choice(cameras),
                "diff": diff,
                "urgency": "urgent" if diff >= 30 else "high" if diff >= 20 else "normal"
            }
        })
    return events


def replay(events: list, verbose: bool = False):
    """Replay events through Cortex perception pipeline."""

    import tempfile
    tmp = Path(tempfile.mkdtemp())

    hab = HabituationFilter(cooldown=30.0, base_threshold=15.0, orienting_mult=2.0)
    circadian = CircadianRhythm()
    engine = DecisionEngine()
    notifications = NotificationQueue(CortexConfig(data_dir=tmp))

    # Stats
    total = len(events)
    motion_events = [e for e in events if e.get("type") == "motion"]
    telegram_events = [e for e in events if e.get("type") == "telegram"]

    passed = 0
    filtered = 0
    orienting = 0
    decisions = {}
    hourly = {}
    camera_stats = {}

    print(_cyan("=" * 60))
    print(_bold(_cyan("  Cortex Replay Demo: Real-World Perception Pipeline")))
    print(_cyan("=" * 60))
    print()
    print(f"  {_bold('Total events:')}    {_white(str(total))}")
    print(f"  {_bold('Motion events:')}   {_white(str(len(motion_events)))}")
    print(f"  {_bold('Telegram events:')} {_white(str(len(telegram_events)))}")
    print(f"  {_bold('Other:')}           {_white(str(total - len(motion_events) - len(telegram_events)))}")
    print()

    # Process motion events through Cortex
    for event in motion_events:
        meta = event.get("metadata", {})
        diff = meta.get("diff", 0)
        camera = meta.get("camera", "unknown")
        ts = event.get("timestamp", "")

        # Parse hour for circadian analysis
        try:
            hour = int(ts[11:13])
            hourly[hour] = hourly.get(hour, 0) + 1
        except (ValueError, IndexError):
            hour = 12

        # Camera stats
        if camera not in camera_stats:
            camera_stats[camera] = {"count": 0, "total_diff": 0, "max_diff": 0, "urgent": 0}
        camera_stats[camera]["count"] += 1
        camera_stats[camera]["total_diff"] += diff
        camera_stats[camera]["max_diff"] = max(camera_stats[camera]["max_diff"], diff)
        if diff >= 30:
            camera_stats[camera]["urgent"] += 1

        # Habituation filter
        event_type = f"motion_{camera}"
        should, reason = hab.should_notify(event_type, diff)

        if not should:
            filtered += 1
            if verbose:
                print(f"  {_dim('[FILTERED]')} {camera} diff={diff:.1f} {_dim(f'({reason})')}")
        else:
            passed += 1
            is_orienting = "rienting" in reason
            if is_orienting:
                orienting += 1
                if verbose:
                    print(f"  {_bg_yellow(' ORIENTING ')} {camera} diff={diff:.1f} {_yellow('<- sudden change!')}")

            # Decision engine
            evt = Event(
                source=camera, type="motion",
                content=f"diff={diff:.1f}",
                priority=8 if diff >= 30 else 5 if diff >= 20 else 3,
            )
            action = engine.decide([evt])
            decisions[action.name] = decisions.get(action.name, 0) + 1

            # Push notifications for significant events
            if diff >= 20:
                priority = "urgent" if diff >= 30 else "normal"
                notifications.push(
                    "motion",
                    f"Motion: {camera} (diff={diff:.1f})",
                    priority
                )

    # Results
    print(_magenta("-" * 60))
    print(_bold(_magenta("  CORTEX PERCEPTION RESULTS")))
    print(_magenta("-" * 60))
    print()

    motion_count = len(motion_events)
    reduction = (filtered / motion_count * 100) if motion_count > 0 else 0

    print(f"  {_bold('Input (raw events):')}      {_white(str(motion_count))}")
    print(f"  {_bold('Passed (conscious):')}      {_green(str(passed))} ({passed*100//max(motion_count,1)}%)")
    print(f"  {_bold('Filtered (habituated):')}   {_red(str(filtered))} ({filtered*100//max(motion_count,1)}%)")
    print(f"  {_bold('Orienting responses:')}     {_yellow(str(orienting))}")
    print(f"  {_bold('Cognitive load reduction:')} {_bg_green(f' {reduction:.0f}% ')}")
    print()

    # Camera breakdown
    print(_bold("  Camera Breakdown:"))
    for cam, stats in sorted(camera_stats.items()):
        avg = stats["total_diff"] / max(stats["count"], 1)
        urgent_str = _red(str(stats['urgent'])) if stats['urgent'] > 0 else "0"
        print(f"    {_cyan(cam)}: {stats['count']} events, avg_diff={avg:.1f}, "
              f"max={stats['max_diff']:.1f}, urgent={urgent_str}")
    print()

    # Decision engine results
    if decisions:
        print(_bold("  Decision Engine Actions:"))
        for action, count in sorted(decisions.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"    {_cyan(action)}: {count}")
        print()

    # Circadian pattern
    print(_bold("  Circadian Pattern (events/hour):"))
    if hourly:
        max_count = max(hourly.values())
        for h in range(24):
            count = hourly.get(h, 0)
            if count > 0:
                bar_len = int(count / max(max_count, 1) * 30)
                # Color bars by time of day
                if 6 <= h < 12:
                    bar = _yellow("\u2588" * bar_len)  # morning
                elif 12 <= h < 18:
                    bar = _green("\u2588" * bar_len)   # afternoon
                elif 18 <= h < 22:
                    bar = _cyan("\u2588" * bar_len)    # evening
                else:
                    bar = _magenta("\u2588" * bar_len)  # night
                print(f"    {_dim(f'{h:02d}:00')}  {count:3d}  {bar}")
    print()

    # Notifications summary
    pending = notifications.get_unread()
    print(f"  {_bold('Notifications queued:')} {_white(str(len(pending)))}")
    if pending:
        for n in pending[:5]:
            msg = n.get("message", str(n))
            print(f"    {_dim('-')} {msg[:70]}")
        if len(pending) > 5:
            print(f"    {_dim(f'... and {len(pending) - 5} more')}")

    print()
    print(_cyan("=" * 60))
    print(_bold(_cyan("  This is what cognitive perception looks like:")))
    print(f"  {_white(str(motion_count))} raw stimuli {_cyan('->')} {_green(str(passed))} conscious events")
    print(f"  {_bg_green(f' {reduction:.0f}% ')} of noise filtered by habituation")
    print(_cyan("=" * 60))

    return {
        "total_events": total,
        "motion_events": motion_count,
        "passed": passed,
        "filtered": filtered,
        "orienting": orienting,
        "reduction_pct": reduction,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cortex Replay Demo")
    parser.add_argument("--log", type=str, help="Path to event_log.jsonl")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    events = load_events(args.log)
    if events:
        replay(events, verbose=args.verbose)
    else:
        print("No events to replay.")
