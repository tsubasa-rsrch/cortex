"""Cortex CLI entry points."""

import argparse


def replay_main():
    """Entry point for cortex-replay command."""
    parser = argparse.ArgumentParser(
        description="Replay real-world events through Cortex perception pipeline"
    )
    parser.add_argument("--log", type=str, help="Path to event_log.jsonl")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    from .replay import load_events, replay

    events = load_events(args.log)
    if events:
        replay(events, verbose=args.verbose)
    else:
        print("No events to replay.")
