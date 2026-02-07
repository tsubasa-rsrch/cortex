#!/usr/bin/env python3
"""Cortex Replay Demo: Real-World Data Pipeline
=============================================
Replays 1,155 real events from a 22-hour daemon session through
the Cortex perception pipeline to demonstrate cognitive filtering.

Data source: tsubasa-daemon motion detection + Telegram messages
  - 944 motion events from bedroom/kitchen cameras
  - 211 Telegram messages (content sanitized for privacy)

This is NOT synthetic data. This is what happens when you give
an AI agent real eyes (cameras) and let it watch the world.

Usage:
    python3 replay_demo.py [--log PATH] [--verbose]

Or via the installed CLI:
    cortex-replay [--log PATH] [--verbose]
"""

import sys
from pathlib import Path

# Allow running from examples/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from cortex.replay import load_events, replay  # noqa: E402

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
