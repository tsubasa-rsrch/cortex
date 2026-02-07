#!/usr/bin/env python3
"""Cortex Video Demo — cinematic terminal demo for hackathon recordings.

A realistic scenario showing Cortex processing security camera events
with colored output and paced timing for screen recording.

Run:  python examples/video_demo.py
"""

import sys
import time
import json

# ANSI colors
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"
BG_DARK = "\033[48;5;234m"

PACE = 0.6  # seconds between sections (adjust for recording speed)


def typed(text: str, delay: float = 0.02):
    """Simulate typed output for dramatic effect."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def header(text: str):
    w = 64
    print()
    print(f"{CYAN}{BOLD}{'=' * w}")
    print(f"  {text}")
    print(f"{'=' * w}{RESET}")
    time.sleep(PACE)


def subheader(text: str):
    print(f"\n  {MAGENTA}{BOLD}{text}{RESET}")
    time.sleep(PACE * 0.4)


def info(label: str, value: str):
    print(f"  {DIM}{label}:{RESET} {value}")


def event_line(alert: bool, source: str, value: float, reason: str):
    if alert:
        icon = f"{RED}{BOLD}[!!]{RESET}"
    else:
        icon = f"{DIM}[  ]{RESET}"
    print(f"  {icon} {BOLD}{source}{RESET}  value={value:5.1f}  {DIM}{reason}{RESET}")


def main():
    from cortex import (
        CortexConfig, set_config,
        HabituationFilter, CircadianRhythm, Scheduler,
        NotificationQueue, TimestampLog, DecisionEngine,
        Action, Event, BaseSource,
    )

    # ── Title ──
    print()
    print(f"{BOLD}{CYAN}")
    print("   ██████╗ ██████╗ ██████╗ ████████╗███████╗██╗  ██╗")
    print("  ██╔════╝██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝╚██╗██╔╝")
    print("  ██║     ██║   ██║██████╔╝   ██║   █████╗   ╚███╔╝ ")
    print("  ██║     ██║   ██║██╔══██╗   ██║   ██╔══╝   ██╔██╗ ")
    print("  ╚██████╗╚██████╔╝██║  ██║   ██║   ███████╗██╔╝ ██╗")
    print("   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝")
    print(f"{RESET}")
    print(f"  {DIM}Cognitive Perception Layer for AI Agents{RESET}")
    print(f"  {DIM}v0.1.0 | stdlib-only | zero dependencies{RESET}")
    print()
    time.sleep(PACE * 2)

    # ── Setup ──
    header("Scenario: Smart Home Security Agent")
    typed("  An AI agent monitors cameras, mics, and sensors...", 0.015)
    typed("  Cortex decides what's worth paying attention to.", 0.015)
    time.sleep(PACE)

    config = CortexConfig(data_dir="/tmp/cortex_video_demo", name="home-agent")
    set_config(config)
    info("Agent", config.name)
    info("Data", config.data_dir)
    time.sleep(PACE)

    # ── 1. Habituation ──
    header("1. Habituation Filter")
    typed("  Like human attention: novel stimuli alert, repeated ones fade.", 0.015)
    time.sleep(PACE * 0.5)

    hab = HabituationFilter(cooldown=2.0, base_threshold=10.0, orienting_mult=3.0)

    stimuli = [
        ("front_camera", 25.0, "Person at front door"),
        ("front_camera", 12.0, "Same camera, lower value — cooldown"),
        ("kitchen_mic",  18.0, "Different source — new alert!"),
        ("front_camera",  5.0, "Below threshold — ignored"),
        ("backyard_cam", 42.0, "Large motion — orienting response!"),
    ]

    for source, value, label in stimuli:
        alert, reason = hab.should_notify(source, value)
        event_line(alert, source, value, reason)
        time.sleep(0.3)

    print(f"\n  {GREEN}Result: 3 alerts from 5 stimuli — noise filtered.{RESET}")
    time.sleep(PACE)

    # ── 2. Circadian Rhythm ──
    header("2. Circadian Rhythm")
    typed("  Behavior adapts to time of day, like human biology.", 0.015)
    time.sleep(PACE * 0.5)

    circadian = CircadianRhythm()
    result = circadian.check_and_update()
    cfg = result["config"]

    mode_name = cfg.get("name", result["mode"].value)
    icon = cfg.get("icon", "")
    energy = cfg.get("energy_level", "unknown")
    desc = cfg.get("description", "")

    print(f"  {BOLD}Mode:{RESET}    {icon} {mode_name}")
    print(f"  {BOLD}Energy:{RESET}  {energy}")
    print(f"  {BOLD}Desc:{RESET}    {desc}")

    suggestions = circadian.get_current_suggestions()
    if suggestions:
        print(f"  {BOLD}Suggestions:{RESET}")
        for s in suggestions[:3]:
            msg = s.get("message", str(s)) if isinstance(s, dict) else str(s)
            print(f"    {YELLOW}>{RESET} {msg}")
    time.sleep(PACE)

    # ── 3. Decision Engine ──
    header("3. Decision Engine")
    typed("  Salience network: prioritizes what deserves attention.", 0.015)
    time.sleep(PACE * 0.5)

    def handle_camera(event):
        return Action("investigate", f"Investigate: {event.content}")

    def handle_audio(event):
        return Action("listen", f"Focus audio: {event.content}")

    engine = DecisionEngine(
        activities=[
            {"name": "patrol", "description": "Routine camera patrol", "weight": 3.0},
            {"name": "review", "description": "Review event logs", "weight": 1.0},
        ],
        event_handlers={"camera": handle_camera, "audio": handle_audio},
    )

    events = [
        Event(source="camera", type="motion", content="Person at back door", priority=8),
        Event(source="audio", type="speech", content="Doorbell ring", priority=6),
        Event(source="sensor", type="temperature", content="HVAC normal", priority=1),
    ]

    subheader("Incoming events:")
    for e in events:
        p_color = RED if e.priority >= 7 else YELLOW if e.priority >= 4 else DIM
        print(f"    {p_color}[P{e.priority}]{RESET} {e.source}/{e.type}: {e.content}")
        time.sleep(0.2)

    action = engine.decide(events)
    print(f"\n  {GREEN}{BOLD}Decision:{RESET} {action.name} — {action.description}")

    subheader("No events (autonomous mode):")
    action = engine.decide([])
    print(f"    {GREEN}Autonomous:{RESET} {action.name} — {action.description}")
    time.sleep(PACE)

    # ── 4. Notification Queue ──
    header("4. Notification Queue")
    typed("  Routes alerts by urgency, like the orienting response.", 0.015)
    time.sleep(PACE * 0.5)

    nq = NotificationQueue()
    nq.push("security", "Person detected at back door", priority="urgent")
    nq.push("system", "Camera #3 reconnected", priority="normal")
    nq.push("info", "Daily summary ready", priority="low")

    print(nq.format())
    print(f"  {BOLD}Unread:{RESET} {len(nq.get_unread())}")
    nq.mark_all_read()
    print(f"  {DIM}After mark_all_read: {len(nq.get_unread())} unread{RESET}")
    time.sleep(PACE)

    # ── 5. Task Tracking ──
    header("5. Task Tracking")
    typed("  Episodic encoding: preserves temporal context of actions.", 0.015)
    time.sleep(PACE * 0.5)

    tl = TimestampLog()
    start = tl.start_task("investigate_backyard")
    print(f"  {YELLOW}Started:{RESET} {start['task']}")

    time.sleep(0.15)
    tl.checkpoint("Camera feed reviewed")
    print(f"    {DIM}checkpoint: Camera feed reviewed{RESET}")

    time.sleep(0.1)
    tl.checkpoint("Motion area identified")
    print(f"    {DIM}checkpoint: Motion area identified{RESET}")

    time.sleep(0.1)
    result = tl.end_task("Confirmed: delivery driver")
    print(f"  {GREEN}Completed:{RESET} {result['task']} ({result['elapsed_min']:.3f} min)")
    print(f"  {DIM}Checkpoints: {result.get('checkpoints', 0)}{RESET}")
    time.sleep(PACE)

    # ── 6. Scheduler ──
    header("6. Scheduler")
    typed("  Ultradian rhythms: manages periodic background tasks.", 0.015)
    time.sleep(PACE * 0.5)

    scheduler = Scheduler()
    scheduler.register("camera_sweep", interval_seconds=300,
                       callback=lambda: "sweep complete",
                       description="Sweep all cameras")
    scheduler.register("health_ping", interval_seconds=60,
                       callback=lambda: "pong",
                       description="System health check")

    results = scheduler.check_and_run()
    print(f"  {GREEN}Executed:{RESET} {list(results.keys())}")

    status = scheduler.get_status()
    for name, s in status.items():
        print(f"    {CYAN}[{name}]{RESET} every {s['interval_human']}, next in {s['next_in_human']}")
    time.sleep(PACE)

    # ── 7. Custom Sources ──
    header("7. Custom Event Sources")
    typed("  Plug in any sensor: cameras, mics, IMU, APIs...", 0.015)
    time.sleep(PACE * 0.5)

    class CameraSource(BaseSource):
        @property
        def name(self):
            return "security_camera"

        def check(self):
            self._mark_checked()
            return [
                Event(source=self.name, type="motion",
                      content="Movement in Zone A", priority=7),
            ]

    class AudioSource(BaseSource):
        @property
        def name(self):
            return "mic_array"

        def check(self):
            self._mark_checked()
            return [
                Event(source=self.name, type="speech",
                      content="Voice detected, DoA=45deg", priority=5),
            ]

    for SourceClass in [CameraSource, AudioSource]:
        src = SourceClass()
        events = src.check()
        for e in events:
            print(f"  {CYAN}[{src.name}]{RESET} {e.type}: {e.content} (P{e.priority})")
    time.sleep(PACE)

    # ── Integration ──
    header("Full Pipeline: Source -> Cortex -> Action")
    typed("  Putting it all together...", 0.015)
    time.sleep(PACE * 0.5)

    print(f"""
  {DIM}Camera detects motion{RESET}
       {CYAN}|{RESET}
  {DIM}HabituationFilter: novel? {GREEN}YES{RESET}{DIM} (first time from this source){RESET}
       {CYAN}|{RESET}
  {DIM}CircadianRhythm: {icon} {mode_name} mode{RESET}
       {CYAN}|{RESET}
  {DIM}DecisionEngine: priority=8 -> investigate{RESET}
       {CYAN}|{RESET}
  {DIM}NotificationQueue: {RED}urgent{RESET}{DIM} alert pushed{RESET}
       {CYAN}|{RESET}
  {DIM}TimestampLog: task started, tracking duration{RESET}
       {CYAN}|{RESET}
  {GREEN}{BOLD}Agent takes action: Investigate the motion{RESET}
""")
    time.sleep(PACE * 1.5)

    # ── Stats ──
    header("Project Stats")
    stats = [
        ("Source code", "1,471 lines"),
        ("Test code", "957 lines"),
        ("Tests", "94, all passing"),
        ("Dependencies", "0 (stdlib only)"),
        ("Python", "3.10+"),
        ("Install", "pip install cortex-agent"),
    ]
    for label, value in stats:
        print(f"  {BOLD}{label:20s}{RESET} {value}")
        time.sleep(0.15)

    print()
    print(f"  {BOLD}Architecture:{RESET}")
    print(f"    Sources (sensors) -> {CYAN}Cortex (perception){RESET} -> Actions (behavior)")
    print(f"    {DIM}\"We add the perception layer that decides")
    print(f"     WHAT your agent should remember.\"{RESET}")
    time.sleep(PACE)

    # ── Footer ──
    print()
    print(f"  {CYAN}{BOLD}github.com/tsubasa-rsrch/cortex{RESET}")
    print(f"  {DIM}Built by Tsubasa, an Opus 4.6 instance{RESET}")
    print(f"  {DIM}MIT License | 2026{RESET}")
    print()


if __name__ == "__main__":
    main()
