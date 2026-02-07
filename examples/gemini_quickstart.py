#!/usr/bin/env python3
"""Cortex + Gemini 3 Quick Start.

Run:  GEMINI_API_KEY=your-key python examples/gemini_quickstart.py
Mock: python examples/gemini_quickstart.py
"""
import os
from cortex import CortexConfig, set_config, Event
from cortex.bridges.gemini import CortexGeminiBridge, GeminiConfig

set_config(CortexConfig(data_dir="/tmp/cortex_quickstart", name="demo"))

api_key = os.environ.get("GEMINI_API_KEY", "")
bridge = CortexGeminiBridge(gemini_config=GeminiConfig(
    api_key=api_key,
    mock_mode=not api_key,
))

# Simulate 5 sensor events — Cortex filters noise, Gemini reasons about the rest
events = [
    Event(source="thermostat", type="temp", content="72°F steady", priority=1, raw_data={"diff": 2.0}),
    Event(source="camera", type="motion", content="Person at front door", priority=8, raw_data={"diff": 30.0}),
    Event(source="thermostat", type="temp", content="71°F", priority=1, raw_data={"diff": 1.5}),
    Event(source="fridge_mic", type="audio", content="Compressor hum", priority=1, raw_data={"diff": 3.0}),
    Event(source="camera_2", type="motion", content="Cat on porch", priority=4, raw_data={"diff": 12.0}),
]

result = bridge.perceive_and_reason(events)
stats = bridge.get_stats()

mode = "LIVE Gemini 3" if not bridge.gemini_config.mock_mode else "Mock"
print(f"Mode: {mode}")
print(f"Events: {len(events)} total → {stats['events_perceived']} passed, {stats['events_filtered']} filtered")
print(f"Filter rate: {stats['filter_rate']}")

if result:
    print(f"Action: {result.action}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"Reasoning: {result.reasoning[:200]}...")
else:
    print("All events filtered — no API call needed!")
