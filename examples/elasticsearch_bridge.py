#!/usr/bin/env python3
"""Cortex-Elasticsearch bridge demo — perception-filtered indexing.

Run:  python examples/elasticsearch_bridge.py

Shows how Cortex filters sensor events through cognitive mechanisms
before indexing to Elasticsearch, reducing noise and prioritizing
what matters.
"""

from cortex import CortexConfig, set_config, Event, BaseSource
from cortex.bridges.elasticsearch import CortexElasticBridge, ESConfig


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


class SimulatedCamera(BaseSource):
    """Simulated camera that generates motion events."""

    def __init__(self, events_to_emit):
        self._events = list(events_to_emit)
        self._index = 0

    @property
    def name(self) -> str:
        return "sim_camera"

    def check(self):
        if self._index < len(self._events):
            event = self._events[self._index]
            self._index += 1
            return [event]
        return []


def main():
    separator("Cortex-Elasticsearch Bridge Demo")

    config = CortexConfig(data_dir="/tmp/cortex_es_demo", name="es-demo")
    set_config(config)

    # --- 1. Create bridge in mock mode ---
    separator("1. Bridge Setup (mock mode)")

    bridge = CortexElasticBridge()
    stats = bridge.get_stats()
    print(f"  Mode: {'mock' if stats['mock_mode'] else 'production'}")
    print(f"  Circadian: {stats['circadian_mode']}")
    print(f"  Index prefix: {stats['index_prefix']}")

    # --- 2. Index events with filtering ---
    separator("2. Index Events (cognitive filtering)")

    events = [
        Event(source="camera", type="motion", content="Person entered lobby",
              priority=8, raw_data={"diff": 25.0}),
        Event(source="camera", type="motion", content="Tree swaying in wind",
              priority=3, raw_data={"diff": 4.0}),
        Event(source="camera", type="motion", content="Car alarm triggered",
              priority=9, raw_data={"diff": 45.0}),
        Event(source="audio", type="sound", content="Background hum",
              priority=1, raw_data={"volume": 0.02}),
        Event(source="audio", type="sound", content="Glass breaking",
              priority=9, raw_data={"volume": 0.95}),
    ]

    for event in events:
        result = bridge.index_event(event)
        status = f"INDEXED (id={result.doc_id})" if result else "FILTERED"
        icon = "!!" if result else "  "
        print(f"  {icon} [{event.source}] {event.content}")
        print(f"       diff/vol={list(event.raw_data.values())[0]}, "
              f"priority={event.priority} → {status}")

    # --- 3. Agent context ---
    separator("3. Agent Builder Context")

    ctx = bridge.get_agent_context()
    perception = ctx["cortex_perception"]
    print(f"  Mode: {perception['circadian_mode']}")
    print(f"  Summary: {perception['perception_summary']}")
    print(f"  Unread: {perception['unread_notifications']}")
    print(f"  Recent events: {len(perception['recent_events'])}")
    for evt in perception["recent_events"]:
        print(f"    [{evt['source']}] {evt['content']} (p={evt['priority']})")

    # --- 4. System prompt injection ---
    separator("4. System Prompt with Cortex Context")

    prompt = bridge.build_agent_system_prompt(
        "You are a security monitoring agent."
    )
    print(prompt)

    # --- 5. Perception loop demo ---
    separator("5. Perception Loop (3 iterations)")

    # Create a simulated source
    sim_events = [
        Event(source="sim_cam", type="motion", content="Door opened",
              priority=7, raw_data={"diff": 20.0}),
        Event(source="sim_cam", type="motion", content="Nothing interesting",
              priority=2, raw_data={"diff": 2.0}),
        Event(source="sim_cam", type="motion", content="Intruder detected!",
              priority=10, raw_data={"diff": 50.0}),
    ]

    source = SimulatedCamera(sim_events)
    indexed = bridge.run_perception_loop(
        sources=[source],
        interval=0.1,
        max_iterations=3,
    )

    print(f"  Iterations: 3")
    print(f"  Events indexed: {len(indexed)}")
    for ie in indexed:
        print(f"    [{ie.doc_id}] {ie.event.content}")

    # --- 6. Production config example ---
    separator("6. Production Configuration (not connected)")

    prod_config = ESConfig(
        es_url="https://my-cluster.es.io:443",
        api_key="base64-encoded-api-key",
        index_prefix="cortex-prod",
        mock_mode=False,
    )
    print(f"  URL: {prod_config.es_url}")
    print(f"  Index: {prod_config.index_prefix}-YYYY.MM.DD")
    print(f"  Mock: {prod_config.mock_mode}")
    print("  (Not connecting — just showing config)")

    # --- Summary ---
    separator("Summary")

    final_stats = bridge.get_stats()
    print(f"  Total indexed: {final_stats['total_indexed']}")
    print(f"  Filtered out: {len(events) + 3 - final_stats['total_indexed']} events")
    print(f"  Circadian mode: {final_stats['circadian_mode']}")
    print()
    print("  Cortex filtered noise BEFORE it reached Elasticsearch.")
    print("  Only novel, significant events made it through.")
    print()


if __name__ == "__main__":
    main()
