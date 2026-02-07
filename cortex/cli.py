"""Cortex CLI entry points."""

import argparse
import sys


def replay_main():
    """Entry point for cortex-replay command."""
    parser = argparse.ArgumentParser(
        description="Replay real-world events through Cortex perception pipeline"
    )
    parser.add_argument("--log", type=str, help="Path to event_log.jsonl")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    # Import here to avoid circular imports
    from pathlib import Path

    # Reuse the replay_demo logic
    sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))
    try:
        from examples.replay_demo import load_events, replay
    except ImportError:
        # Fallback: inline minimal version
        from cortex import (
            CortexConfig,
            HabituationFilter,
            CircadianRhythm,
            DecisionEngine,
            NotificationQueue,
        )
        from cortex.sources.base import Event
        import json
        import tempfile

        path = args.log
        if path is None:
            candidates = [
                Path.home() / ".tsubasa-daemon" / "memory" / "event_log.jsonl",
                Path(__file__).parent.parent / "examples" / "sample_events.jsonl",
            ]
            for p in candidates:
                if p.exists():
                    path = str(p)
                    break

        if not path or not Path(path).exists():
            print("No event log found. Install sample data or provide --log path.")
            sys.exit(1)

        events = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        motion_events = [e for e in events if e.get("type") == "motion"]
        tmp = Path(tempfile.mkdtemp())
        hab = HabituationFilter(cooldown=30.0, base_threshold=15.0, orienting_mult=2.0)
        engine = DecisionEngine()
        notifications = NotificationQueue(CortexConfig(data_dir=tmp))

        passed = 0
        filtered = 0
        for event in motion_events:
            meta = event.get("metadata", {})
            diff = meta.get("diff", 0)
            camera = meta.get("camera", "unknown")
            event_type = f"motion_{camera}"
            should, reason = hab.should_notify(event_type, diff)
            if should:
                passed += 1
            else:
                filtered += 1

        total = len(motion_events)
        reduction = (filtered / total * 100) if total > 0 else 0
        print(f"Cortex Replay: {total} events → {passed} conscious ({reduction:.0f}% filtered)")
        return

    events = load_events(args.log)
    if events:
        replay(events, verbose=args.verbose)
    else:
        print("No events to replay.")
