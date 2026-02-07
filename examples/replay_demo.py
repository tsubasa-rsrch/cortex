#!/usr/bin/env python3
"""
Cortex Replay Demo: Real-World Data Pipeline
=============================================
Replays 1,141 real events from a 22-hour daemon session through
the Cortex perception pipeline to demonstrate cognitive filtering.

Data source: tsubasa-daemon motion detection + Telegram messages
  - 932 motion events from bedroom/kitchen cameras
  - 207 Telegram messages
  - 2 system events

This is NOT synthetic data. This is what happens when you give
an AI agent real eyes (cameras) and let it watch the world.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cortex import CortexConfig, HabituationFilter, CircadianRhythm, DecisionEngine, NotificationQueue
from cortex.sources.base import Event


def load_events(path: str = None) -> list:
    """Load real events from daemon event log."""
    if path is None:
        candidates = [
            Path.home() / ".tsubasa-daemon" / "memory" / "event_log.jsonl",
            Path(__file__).parent / "sample_events.jsonl",
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

    print("=" * 60)
    print("  Cortex Replay Demo: Real-World Perception Pipeline")
    print("=" * 60)
    print()
    print(f"  Total events:    {total}")
    print(f"  Motion events:   {len(motion_events)}")
    print(f"  Telegram events: {len(telegram_events)}")
    print(f"  Other:           {total - len(motion_events) - len(telegram_events)}")
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
                print(f"  [FILTERED] {camera} diff={diff:.1f} ({reason})")
        else:
            passed += 1
            is_orienting = "rienting" in reason
            if is_orienting:
                orienting += 1
                if verbose:
                    print(f"  [ORIENTING] {camera} diff={diff:.1f} <- sudden change!")

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
    print("-" * 60)
    print("  CORTEX PERCEPTION RESULTS")
    print("-" * 60)
    print()

    motion_count = len(motion_events)
    reduction = (filtered / motion_count * 100) if motion_count > 0 else 0

    print(f"  Input (raw events):      {motion_count}")
    print(f"  Passed (conscious):      {passed} ({passed*100//max(motion_count,1)}%)")
    print(f"  Filtered (habituated):   {filtered} ({filtered*100//max(motion_count,1)}%)")
    print(f"  Orienting responses:     {orienting}")
    print(f"  Cognitive load reduction: {reduction:.0f}%")
    print()

    # Camera breakdown
    print("  Camera Breakdown:")
    for cam, stats in sorted(camera_stats.items()):
        avg = stats["total_diff"] / max(stats["count"], 1)
        print(f"    {cam}: {stats['count']} events, avg_diff={avg:.1f}, "
              f"max={stats['max_diff']:.1f}, urgent={stats['urgent']}")
    print()

    # Decision engine results
    if decisions:
        print("  Decision Engine Actions:")
        for action, count in sorted(decisions.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"    {action}: {count}")
        print()

    # Circadian pattern
    print("  Circadian Pattern (events/hour):")
    if hourly:
        max_count = max(hourly.values())
        for h in range(24):
            count = hourly.get(h, 0)
            if count > 0:
                bar_len = int(count / max(max_count, 1) * 30)
                bar = "\u2588" * bar_len
                status = circadian.get_status()
                print(f"    {h:02d}:00  {count:3d}  {bar}")
    print()

    # Notifications summary
    pending = notifications.get_unread()
    print(f"  Notifications queued: {len(pending)}")
    if pending:
        for n in pending[:5]:
            msg = n.get("message", str(n))
            print(f"    - {msg[:70]}")
        if len(pending) > 5:
            print(f"    ... and {len(pending) - 5} more")

    print()
    print("=" * 60)
    print("  This is what cognitive perception looks like:")
    print(f"  {motion_count} raw stimuli -> {passed} conscious events")
    print(f"  {reduction:.0f}% of noise filtered by habituation")
    print("=" * 60)

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
