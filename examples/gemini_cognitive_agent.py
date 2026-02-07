#!/usr/bin/env python3
"""Cortex + Gemini 3 Cognitive Agent Demo.

Shows how Cortex perception + Gemini 3 reasoning create a complete
cognitive agent that filters noise and reasons about what matters.

The key insight: most AI agents send everything to the LLM.
Cortex filters first, saving ~60-80% of API calls while only
reasoning about genuinely novel, important events.

Run (mock mode):  python examples/gemini_cognitive_agent.py
Run (real API):   GEMINI_API_KEY=your-key python examples/gemini_cognitive_agent.py

Requires: pip install cortex-agent
"""

import os
import sys
import time

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

PACE = 0.4


def header(text: str):
    w = 64
    print(f"\n{CYAN}{BOLD}{'=' * w}")
    print(f"  {text}")
    print(f"{'=' * w}{RESET}")
    time.sleep(PACE)


def typed(text: str, delay: float = 0.015):
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def main():
    from cortex import CortexConfig, set_config, Event, BaseSource
    from cortex.bridges.gemini import CortexGeminiBridge, GeminiConfig

    # ── Title ──
    print(f"\n{BOLD}{CYAN}")
    print("   ██████╗ ██████╗ ██████╗ ████████╗███████╗██╗  ██╗")
    print("  ██╔════╝██╔═══██╗██╔══██╗╚══██╔══╝██╔════╝╚██╗██╔╝")
    print("  ██║     ██║   ██║██████╔╝   ██║   █████╗   ╚███╔╝ ")
    print("  ██║     ██║   ██║██╔══██╗   ██║   ██╔══╝   ██╔██╗ ")
    print("  ╚██████╗╚██████╔╝██║  ██║   ██║   ███████╗██╔╝ ██╗")
    print("   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝")
    print(f"{RESET}")
    print(f"  {DIM}Cognitive Perception Layer + Gemini 3 Reasoning{RESET}")
    print(f"  {DIM}Cortex filters noise. Gemini 3 reasons about what matters.{RESET}")
    print()
    time.sleep(PACE * 2)

    # ── Setup ──
    header("Setup: Cognitive Agent Configuration")
    config = CortexConfig(data_dir="/tmp/cortex_gemini_demo", name="smart-home")
    set_config(config)

    # Check for real API key
    api_key = os.environ.get("GEMINI_API_KEY", "")
    mock_mode = not api_key

    gemini_config = GeminiConfig(
        api_key=api_key,
        model="gemini-3-flash-preview",
        mock_mode=mock_mode,
    )

    bridge = CortexGeminiBridge(gemini_config=gemini_config)

    mode_str = f"{RED}MOCK{RESET}" if mock_mode else f"{GREEN}LIVE (Gemini 3){RESET}"
    print(f"  {BOLD}Agent:{RESET}  {config.name}")
    print(f"  {BOLD}Mode:{RESET}   {mode_str}")
    print(f"  {BOLD}Model:{RESET}  {gemini_config.model}")
    if mock_mode:
        print(f"  {DIM}Set GEMINI_API_KEY to use real Gemini 3 API{RESET}")
    time.sleep(PACE)

    # ── Scenario 1: Normal Activity ──
    header("Scenario 1: Routine Activity (Afternoon)")
    typed("  A smart home receives 10 sensor events per minute.")
    typed("  Most are routine. What deserves attention?")
    time.sleep(PACE * 0.5)

    routine_events = [
        Event(source="thermostat", type="temp", content="HVAC at 72°F", priority=1, raw_data={"diff": 2.0}),
        Event(source="front_camera", type="motion", content="Mail carrier at door", priority=5, raw_data={"diff": 15.0}),
        Event(source="thermostat", type="temp", content="HVAC at 71°F", priority=1, raw_data={"diff": 1.5}),
        Event(source="kitchen_mic", type="audio", content="Refrigerator hum", priority=1, raw_data={"diff": 3.0}),
        Event(source="backyard_cam", type="motion", content="Squirrel on fence", priority=3, raw_data={"diff": 8.0}),
    ]

    print(f"\n  {MAGENTA}{BOLD}Incoming events (5):{RESET}")
    for e in routine_events:
        p_color = RED if e.priority >= 7 else YELLOW if e.priority >= 4 else DIM
        print(f"    {p_color}[P{e.priority}]{RESET} {e.source}: {e.content}")
        time.sleep(0.15)

    print(f"\n  {CYAN}{BOLD}Step 1: Cortex Perception (filter noise){RESET}")
    passed = bridge.perceive(routine_events)
    print(f"  {GREEN}→ {len(passed)} events passed filters, {len(routine_events) - len(passed)} filtered out{RESET}")
    for e in passed:
        print(f"    {GREEN}✓{RESET} [{e.source}] {e.content}")
    time.sleep(PACE)

    if passed:
        print(f"\n  {CYAN}{BOLD}Step 2: Gemini 3 Reasoning (only on filtered events){RESET}")
        result = bridge.perceive_and_reason(routine_events)
        if result:
            print(f"  {BOLD}Action:{RESET}     {result.action}")
            print(f"  {BOLD}Confidence:{RESET} {result.confidence:.0%}")
            print(f"  {BOLD}Reasoning:{RESET}  {result.reasoning[:120]}...")
    time.sleep(PACE)

    stats = bridge.get_stats()
    print(f"\n  {DIM}API calls saved: {stats['events_filtered']} events filtered → "
          f"only {stats['api_calls']} API call needed{RESET}")

    # ── Scenario 2: Urgent Event ──
    header("Scenario 2: Urgent Event (Night Mode)")
    typed("  3 AM. Camera detects a person at the back door.")
    typed("  Cortex night mode heightens vigilance.")
    time.sleep(PACE * 0.5)

    urgent_events = [
        Event(source="backyard_cam", type="motion",
              content="Person detected at back door at 3 AM",
              priority=9, raw_data={"diff": 45.0}),
        Event(source="doorbell_mic", type="audio",
              content="No doorbell ring (unusual)",
              priority=7, raw_data={"diff": 22.0}),
    ]

    print(f"\n  {RED}{BOLD}⚠ HIGH PRIORITY EVENTS:{RESET}")
    for e in urgent_events:
        print(f"    {RED}[P{e.priority}]{RESET} {e.source}: {e.content}")
        time.sleep(0.2)

    print(f"\n  {CYAN}{BOLD}Step 1: Cortex Perception{RESET}")
    passed = bridge.perceive(urgent_events)
    print(f"  {GREEN}→ {len(passed)}/{len(urgent_events)} events pass filters (all novel, all urgent){RESET}")

    print(f"\n  {CYAN}{BOLD}Step 2: Gemini 3 Reasoning{RESET}")
    # Build a prompt that triggers night mode reasoning
    result = bridge.reason(
        f"Analyze: priority: 9 motion at back door during night hours. "
        f"Late Night mode. No doorbell ring. Person approaching silently."
    )
    conf_color = RED if result.confidence > 0.8 else YELLOW
    print(f"  {BOLD}Action:{RESET}     {RED}{result.action}{RESET}")
    print(f"  {BOLD}Confidence:{RESET} {conf_color}{result.confidence:.0%}{RESET}")
    print(f"  {BOLD}Reasoning:{RESET}")
    # Word wrap reasoning
    words = result.reasoning.split()
    line = "    "
    for w in words:
        if len(line) + len(w) > 70:
            print(line)
            line = "    "
        line += w + " "
    if line.strip():
        print(line)
    time.sleep(PACE)

    # ── Scenario 3: Interactive Query ──
    header("Scenario 3: Interactive Context Query")
    typed("  Ask the cognitive agent: 'What's happened recently?'")
    time.sleep(PACE * 0.5)

    result = bridge.reason_about_context(
        "Summarize what has happened and what you recommend."
    )
    print(f"  {BOLD}Response:{RESET}")
    print(f"    {result.reasoning[:200]}")
    time.sleep(PACE)

    # ── Stats ──
    header("Cognitive Agent Statistics")
    stats = bridge.get_stats()
    stat_items = [
        ("Events perceived", str(stats["events_perceived"])),
        ("Events filtered (noise)", str(stats["events_filtered"])),
        ("Filter rate", stats["filter_rate"]),
        ("Gemini 3 API calls", str(stats["api_calls"])),
        ("Circadian mode", stats["circadian_mode"]),
        ("Model", stats["model"]),
    ]
    for label, value in stat_items:
        print(f"  {BOLD}{label:25s}{RESET} {value}")
        time.sleep(0.1)

    # ── Architecture ──
    print(f"""
  {CYAN}{BOLD}Architecture:{RESET}
    Sensors → {YELLOW}Cortex (perception){RESET} → {MAGENTA}Gemini 3 (reasoning){RESET} → Actions
              habituation filter     deep understanding      alert
              circadian rhythm       contextual reasoning     investigate
              priority assessment    natural language          log
              noise elimination      planning & decisions      ignore

  {DIM}\"Most AI agents send everything to the LLM.
   Cortex filters first — 60-80% noise reduction.
   Gemini 3 only reasons about what matters.\"{RESET}
""")
    time.sleep(PACE)

    # ── Footer ──
    print(f"  {CYAN}{BOLD}github.com/tsubasa-rsrch/cortex{RESET}")
    print(f"  {DIM}Built for the Gemini 3 Hackathon{RESET}")
    print(f"  {DIM}Cortex: perception layer | Gemini 3: reasoning layer{RESET}")
    print(f"  {DIM}MIT License | 2026{RESET}")
    print()


if __name__ == "__main__":
    main()
