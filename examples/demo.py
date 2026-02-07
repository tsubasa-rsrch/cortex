#!/usr/bin/env python3
"""Cortex demo — shows all 7 modules working together.

Run:  python examples/demo.py
"""

import time

from cortex import (
    CortexConfig,
    set_config,
    HabituationFilter,
    CircadianRhythm,
    Scheduler,
    NotificationQueue,
    TimestampLog,
    DecisionEngine,
    Action,
    Event,
    BaseSource,
)


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def main():
    # --- Setup ---
    separator("Cortex Demo — Cognitive Perception for AI Agents")

    config = CortexConfig(data_dir="/tmp/cortex_demo", name="demo-agent")
    set_config(config)
    print(f"Config: data_dir={config.data_dir}, name={config.name}")

    # --- 1. Habituation Filter ---
    separator("1. HabituationFilter — Attention Management")

    hab = HabituationFilter(
        cooldown=2.0,       # Short cooldown for demo
        base_threshold=10.0,
        orienting_mult=3.0,
    )

    stimuli = [
        ("camera_front", 12.0, "Normal motion"),
        ("camera_front", 8.0, "Below threshold"),
        ("camera_front", 15.0, "During cooldown"),
        ("camera_back", 35.0, "Orienting response — different source"),
    ]

    for source, value, label in stimuli:
        alert, reason = hab.should_notify(source, value)
        mark = "!!" if alert else "  "
        print(f"  {mark} [{source}] value={value:5.1f}  {label}")
        print(f"       → {reason}")

    # --- 2. Circadian Rhythm ---
    separator("2. CircadianRhythm — Time-Aware Behavior")

    circadian = CircadianRhythm()
    result = circadian.check_and_update()

    mode = result["mode"]
    cfg = result["config"]
    print(f"  Current mode: {cfg.get('icon', '')} {cfg.get('name', mode.value)}")
    print(f"  Energy level: {cfg.get('energy_level', 'unknown')}")
    print(f"  Description:  {cfg.get('description', '')}")
    print(f"  Activities:   {', '.join(cfg.get('activities', []))}")

    suggestions = circadian.get_current_suggestions()
    if suggestions:
        print(f"  Suggestions:")
        for s in suggestions[:3]:
            if isinstance(s, dict):
                print(f"    - {s.get('message', s.get('text', str(s)))}")
            else:
                print(f"    - {s}")

    # --- 3. Scheduler ---
    separator("3. Scheduler — Periodic Task Management")

    scheduler = Scheduler()

    call_count = {"health": 0, "sync": 0}

    def health_check():
        call_count["health"] += 1
        return "ok"

    def sync_data():
        call_count["sync"] += 1
        return "synced"

    scheduler.register("health_check", interval_seconds=1, callback=health_check,
                       description="Check system health")
    scheduler.register("sync_data", interval_seconds=5, callback=sync_data,
                       description="Sync external data")

    results = scheduler.check_and_run()
    print(f"  First run: {list(results.keys())} executed")

    status = scheduler.get_status()
    for name, info in status.items():
        print(f"  [{name}] interval={info['interval_human']}, "
              f"next_in={info['next_in_human']}")

    # --- 4. Notification Queue ---
    separator("4. NotificationQueue — Agent Communication")

    nq = NotificationQueue()

    nq.push("alert", "Motion detected in lobby", priority="urgent")
    nq.push("message", "New email from alice@example.com")
    nq.push("system", "Backup completed successfully", priority="low")

    print(nq.format())

    print(f"\n  Unread count: {len(nq.get_unread())}")
    nq.mark_all_read()
    print(f"  After mark_all_read: {len(nq.get_unread())} unread")

    # --- 5. Timestamp Log ---
    separator("5. TimestampLog — Task Duration Tracking")

    tl = TimestampLog()

    start = tl.start_task("process_batch")
    print(f"  Started: {start['task']}")

    tl.checkpoint("loaded data")
    time.sleep(0.1)
    tl.checkpoint("processed records")

    result = tl.end_task("complete")
    print(f"  Finished: {result['task']} in {result['elapsed_min']:.3f} min")
    print(f"  Checkpoints: {result.get('checkpoints', 0)}")

    # --- 6. Decision Engine ---
    separator("6. DecisionEngine — Action Selection")

    def handle_camera(event):
        return Action("investigate", f"Investigate: {event.content}")

    engine = DecisionEngine(
        activities=[
            {"name": "explore", "description": "Browse recent feeds", "weight": 5.0},
            {"name": "review", "description": "Review system logs", "weight": 2.0},
            {"name": "learn", "description": "Read documentation", "weight": 1.0},
        ],
        event_handlers={"camera": handle_camera},
    )

    # With events
    events = [
        Event(source="camera", type="motion", content="lobby movement", priority=8),
        Event(source="email", type="message", content="meeting invite", priority=4),
    ]
    action = engine.decide(events)
    print(f"  With events  → {action.name}: {action.description}")

    # Without events (autonomous)
    action = engine.decide([])
    print(f"  No events    → {action.name}: {action.description}")

    # Action with handler
    action = Action("add", "Add numbers", params={"a": 2, "b": 3},
                    handler=lambda a, b: a + b)
    result = action.execute()
    print(f"  Execute      → {result}")

    # --- 7. Custom Source ---
    separator("7. BaseSource — Custom Event Sources")

    class DemoSource(BaseSource):
        @property
        def name(self) -> str:
            return "demo"

        def check(self):
            self._mark_checked()
            return [
                Event(source=self.name, type="heartbeat",
                      content="Demo source is alive", priority=1),
            ]

    src = DemoSource()
    events = src.check()
    print(f"  Source: {src.name}")
    print(f"  Events: {len(events)}")
    for e in events:
        print(f"    [{e.type}] {e.content} (priority={e.priority})")

    # --- Summary ---
    separator("Done")
    print("  7 modules, 0 external dependencies, pure Python 3.10+")
    print("  State persisted to: /tmp/cortex_demo/")
    print("  GitHub: https://github.com/tsubasa-rsrch/cortex")
    print()


if __name__ == "__main__":
    main()
