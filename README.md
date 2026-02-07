# Cortex

[![Tests](https://img.shields.io/badge/tests-111%20passed-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Dependencies](https://img.shields.io/badge/dependencies-zero-orange)]()

Cognitive-science-based perception framework for AI agents. Zero external dependencies, pure Python 3.10+.

Cortex gives your agent a **perception layer** — the cognitive mechanisms that decide *what* is worth paying attention to, *when* to act, and *how* to manage the flow of incoming information. Inspired by human neuroscience (habituation, circadian rhythms, orienting responses), built for practical agent architectures.

## Why Cortex?

Most agent frameworks focus on memory and reasoning. Cortex fills the gap *before* memory — the perception layer that decides **what your agent should remember** in the first place.

```
Sources (sensors/APIs) → Cortex (perception) → Your memory/reasoning layer
```

**Key properties:**
- **stdlib-only** — no pip dependencies, works anywhere Python runs
- **Zero coupling** — each module is independent, use one or all seven
- **Config injection** — one `CortexConfig` object wires everything together
- **Pluggable defaults** — override suggestions, activities, handlers at init time

## Installation

```bash
pip install cortex-agent
# or from source:
git clone https://github.com/tsubasa-rsrch/cortex.git
cd cortex && pip install -e .
```

## Quick Start

```python
from cortex import CortexConfig, set_config
from cortex import HabituationFilter, CircadianRhythm, DecisionEngine, Event

# Configure (optional — defaults to ~/.cortex/)
set_config(CortexConfig(data_dir="/tmp/my_agent", name="demo"))

# 1. Filter noise with habituation
hab = HabituationFilter(base_threshold=15.0)

should_alert, reason = hab.should_notify("camera_1", 25.0)
print(f"Alert: {should_alert} — {reason}")
# Alert: True — Motion (alert, value=25.0 >= threshold=15.0)

should_alert, reason = hab.should_notify("camera_1", 16.0)
print(f"Alert: {should_alert} — {reason}")
# Alert: False — Cooldown (2s < 60s)

# 2. Adapt behavior to time of day
circadian = CircadianRhythm()
status = circadian.check_and_update()
print(f"Mode: {status['mode'].value}, Changed: {status['changed']}")

# 3. Decide what to do
engine = DecisionEngine()
events = [
    Event(source="camera", type="motion", content="Movement detected", priority=8),
    Event(source="api", type="message", content="Hello", priority=3),
]
action = engine.decide(events)
print(f"Action: {action.name} — {action.description}")
# Processes highest-priority event first
```

## Modules

### HabituationFilter

Prevents notification fatigue using three mechanisms from cognitive science:

| Mechanism | What it does | Real-world analogy |
|-----------|-------------|-------------------|
| **Habituation** | Repeated stimuli raise the threshold | You stop noticing the clock ticking |
| **Orienting response** | Abnormally large stimuli always fire | A sudden loud noise gets your attention |
| **Cooldown** | Minimum gap between notifications | Your phone's "do not disturb" timer |

```python
hab = HabituationFilter(
    cooldown=60.0,          # Min seconds between alerts per source
    window=300.0,           # Habituation counting window
    habituate_count=3,      # Detections before habituation kicks in
    habituated_mult=2.0,    # Threshold multiplier when habituated
    orienting_mult=2.0,     # Multiplier for orienting response
    base_threshold=15.0,    # Base detection threshold
)
should_alert, reason = hab.should_notify("sensor_1", value=25.0)
```

### CircadianRhythm

Maps time-of-day to behavioral modes, inspired by cortisol/melatonin cycles:

| Mode | Hours | Energy | Metaphor |
|------|-------|--------|----------|
| Morning | 06-12 | Rising | Information gathering |
| Afternoon | 12-18 | Peak | Deep work |
| Evening | 18-24 | Declining | Reflection |
| Night | 00-06 | Low | Memory consolidation |

```python
circadian = CircadianRhythm()
result = circadian.check_and_update()

# Override defaults with your own suggestions
custom = CircadianRhythm(suggestions={
    "morning": [{"text": "Check inbox", "icon": "mail"}],
    "afternoon": [{"text": "Write code", "icon": "laptop"}],
    "evening": [{"text": "Review PRs", "icon": "search"}],
    "night": [{"text": "Run backups", "icon": "database"}],
})
```

### Scheduler

In-process cron for periodic tasks with persistent state:

```python
from cortex import Scheduler

scheduler = Scheduler()
scheduler.register("health_check", interval_seconds=300, callback=check_health)
scheduler.register("sync_data", interval_seconds=3600, callback=sync)

# In your main loop:
results = scheduler.check_and_run()  # Runs any tasks that are due
status = scheduler.get_status()       # Human-readable timing info
```

### NotificationQueue

File-based notification system for background-to-agent communication:

```python
from cortex import NotificationQueue

nq = NotificationQueue()
nq.push("alert", "Motion detected in lobby", priority="urgent")
nq.push("message", "New email from alice@example.com")

unread = nq.get_unread()
print(nq.format())
# Notifications (2):
#   !!🔔 [09:15] Motion detected in lobby
#   💬 [09:16] New email from alice@example.com

nq.mark_all_read()
```

### TimestampLog

Track task duration with checkpoints:

```python
from cortex import TimestampLog

tl = TimestampLog()
tl.start_task("deploy v2.1")
# ... work ...
tl.checkpoint("tests passed")
# ... more work ...
result = tl.end_task("deployed successfully")
print(f"Took {result['elapsed_min']:.1f} minutes")

status = tl.get_status()  # Current task, time elapsed, checkpoints
```

### DecisionEngine

Routes events to actions, with weighted random selection for idle periods:

```python
from cortex import DecisionEngine, Action, Event

# Custom event handler
def handle_camera(event):
    return Action("investigate", f"Check {event.content}")

engine = DecisionEngine(
    activities=[
        {"name": "explore", "description": "Browse the web", "weight": 3.0},
        {"name": "review", "description": "Review recent logs", "weight": 1.0},
    ],
    event_handlers={"camera": handle_camera},
)

# With events: routes to handler
action = engine.decide([Event(source="camera", type="motion", content="lobby", priority=7)])

# Without events: picks a random activity
action = engine.decide([])
result = action.execute()  # Runs the handler if one is attached
```

### Event Sources (BaseSource)

Create custom input sources by subclassing `BaseSource`:

```python
from cortex import BaseSource, Event

class SlackSource(BaseSource):
    @property
    def name(self) -> str:
        return "slack"

    def check(self) -> list:
        # Your polling logic here
        messages = self._fetch_new_messages()
        return [
            Event(
                source=self.name,
                type="message",
                content=msg["text"],
                author=msg["user"],
                priority=7 if "@agent" in msg["text"] else 3,
            )
            for msg in messages
        ]
```

## ReachyMini Integration

Cortex includes first-class support for [Pollen Robotics' ReachyMini](https://www.pollen-robotics.com/reachy-mini/) — a tabletop robot with a camera, 4-mic array, IMU, and expressive antennas.

```bash
pip install cortex-agent[reachy]
```

Three sensor sources bridge ReachyMini hardware into Cortex's event pipeline:

| Source | Sensor | Event type | What it detects |
|--------|--------|------------|-----------------|
| `ReachyCameraSource` | Camera | `motion` | Frame differencing (prediction error) |
| `ReachyAudioSource` | 4-mic array | `speech` / `sound` | Voice direction (DoA) + loudness |
| `ReachyIMUSource` | Accelerometer | `bump` | Sudden movement / being picked up |

```python
from reachy_mini import ReachyMini
from cortex.sources.reachy import ReachyCameraSource, ReachyAudioSource, ReachyIMUSource

mini = ReachyMini(connection_mode="localhost_only")
camera = ReachyCameraSource(mini, diff_threshold=15.0, min_changed_ratio=0.0668)
audio = ReachyAudioSource(mini, energy_threshold=0.01)
imu = ReachyIMUSource(mini, accel_threshold=2.0)

# Poll in your main loop
events = camera.check() + audio.check() + imu.check()
action = engine.decide(events)
```

The full bridge example (`examples/reachy_bridge.py`) maps perception to physical actions:
- **HabituationFilter** → head tracking (attend to novel stimuli, ignore repeats)
- **CircadianRhythm** → antenna expression (energy/mood throughout the day)
- **DecisionEngine** → action routing (look at speaker, startle on bump)

Run the 8-step demo or live mode:

```bash
# Start mockup simulator
reachy-mini-daemon --mockup-sim --deactivate-audio --localhost-only

# Demo mode (scripted)
python examples/reachy_bridge.py

# Live mode (real-time perception loop)
python examples/reachy_bridge.py --live --interval 0.5
```

## Platform Bridges

Cortex bridges connect perception modules to external platforms. Events are filtered through cognitive mechanisms before reaching the target platform.

### Elasticsearch Bridge

Integrates Cortex with Elasticsearch for time-series event indexing and Agent Builder context injection:

```python
from cortex.bridges.elasticsearch import CortexElasticBridge, ESConfig

# Mock mode (no ES cluster needed)
bridge = CortexElasticBridge()

# Production mode
bridge = CortexElasticBridge(es_config=ESConfig(
    es_url="https://your-cluster.es.io:443",
    api_key="your-api-key",
    index_prefix="cortex-events",
    mock_mode=False,
))

# Filter and index an event (only novel stimuli pass through)
from cortex import Event
event = Event(source="camera", type="motion", content="Movement in lobby", priority=8,
              raw_data={"diff": 25.0})
result = bridge.index_event(event)  # Returns IndexedEvent or None

# Build Agent Builder context with circadian awareness
context = bridge.get_agent_context()
prompt = bridge.build_agent_system_prompt("You are a security agent.")
```

**Integration points:**

| Cortex Module | ES Integration | What it does |
|---------------|---------------|--------------|
| HabituationFilter | Event ingestion | Only index novel stimuli |
| CircadianRhythm | Agent behavior | Adjust system prompts by time of day |
| DecisionEngine | Tool selection | Pre-filter Agent Builder tools |
| NotificationQueue | Conversation context | Inject background events |
| Scheduler | ES\|QL jobs | Periodic health checks and reports |

### Gemini 3 Bridge

Connects Cortex perception with Google Gemini 3 for cognitive reasoning. Cortex filters noise, Gemini 3 reasons about what matters — saving 60-80% of API calls.

```python
from cortex.bridges.gemini import CortexGeminiBridge, GeminiConfig

# Mock mode (no API key needed)
bridge = CortexGeminiBridge()

# Production mode
bridge = CortexGeminiBridge(gemini_config=GeminiConfig(
    api_key="your-gemini-api-key",
    model="gemini-3-flash-preview",
    mock_mode=False,
))

# Full pipeline: filter → reason → act
from cortex import Event
events = [
    Event(source="camera", type="motion", content="Person at door", priority=8,
          raw_data={"diff": 30.0}),
    Event(source="mic", type="audio", content="Doorbell", priority=6,
          raw_data={"diff": 20.0}),
]
result = bridge.perceive_and_reason(events)
if result:
    print(f"Action: {result.action} (confidence: {result.confidence:.0%})")
    print(f"Reasoning: {result.reasoning}")

# Interactive queries with full perception context
response = bridge.reason_about_context("What's happening right now?")

# Check efficiency stats
stats = bridge.get_stats()
print(f"Filter rate: {stats['filter_rate']}")  # e.g. "60.0%"
```

**Architecture:**

```
Sensors → Cortex (perception) → Gemini 3 (reasoning) → Actions
          habituation filter     contextual reasoning    alert
          circadian rhythm       planning & decisions    investigate
          priority assessment    natural language         log
```

Run the demo:

```bash
# Mock mode (no API key)
python examples/gemini_cognitive_agent.py

# Real API
GEMINI_API_KEY=your-key python examples/gemini_cognitive_agent.py
```

## Claude Code MCP Server

Cortex includes a built-in MCP (Model Context Protocol) server that gives any Claude Code session real-time perception capabilities:

```bash
# Install
pip install cortex-agent

# Add to Claude Code
claude mcp add cortex-perception -- python -m cortex.mcp_server
```

Or add to `.mcp.json`:

```json
{
    "mcpServers": {
        "cortex-perception": {
            "command": "python3",
            "args": ["-m", "cortex.mcp_server"]
        }
    }
}
```

**Available tools:**

| Tool | What it does |
|------|-------------|
| `cortex_perception_summary` | Full status: circadian mode, notifications, tasks, schedule |
| `cortex_check_habituation` | Filter noise — only alert on novel/significant stimuli |
| `cortex_circadian_status` | Time-of-day awareness with activity suggestions |
| `cortex_push_notification` | Queue notifications by urgency |
| `cortex_get_notifications` | Retrieve and manage notification queue |
| `cortex_decide` | Route events to actions via salience network |
| `cortex_start_task` / `cortex_checkpoint` / `cortex_end_task` | Track task timing |
| `cortex_schedule` / `cortex_check_schedule` | Register and check periodic tasks |

This turns any Claude Code session into a perception-aware agent that knows *what* to pay attention to and *when* to act.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       Your Agent                              │
│                                                               │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────────────┐ │
│  │ Sources   │→│   Cortex    │→│  Memory / Reasoning       │ │
│  │ (sensors) │  │ (filtering) │  │  (Cognee, LangChain, …)  │ │
│  └──────────┘  └────────────┘  └──────────────────────────┘ │
│       │              │                    │                    │
│  BaseSource     HabituationFilter    ┌───────────────┐      │
│  Event          CircadianRhythm      │  Body / API    │      │
│  ReachyCamera   Scheduler            │  (ReachyMini,  │      │
│  ReachyAudio    NotificationQueue    │   Slack, …)    │      │
│  ReachyIMU      TimestampLog         └───────────────┘      │
│                 DecisionEngine                               │
│                      │                                        │
│              ┌───────────────┐                                │
│              ┌───────────────┐                                │
│              │   Bridges      │                                │
│              │  Gemini 3      │                                │
│              │  Elasticsearch │                                │
│              │  MCP Server    │                                │
│              └───────────────┘                                │
└──────────────────────────────────────────────────────────────┘
```

## Configuration

All stateful modules share a single `CortexConfig`:

```python
from cortex import CortexConfig, set_config

config = CortexConfig(
    data_dir="/path/to/state",  # Where state files are stored (default: ~/.cortex/)
    name="my-agent",            # Agent identifier
)
set_config(config)  # Sets the global config used by all modules
```

Each module also accepts `config=` directly for isolated usage:

```python
hab = HabituationFilter()                        # Uses global config
scheduler = Scheduler(config=my_custom_config)    # Uses its own config
```

## Testing

```bash
pip install pytest
python -m pytest tests/ -v
```

111 tests, <0.5s. Core modules have zero external dependencies; MCP server requires `mcp` package.

## Cognitive Science Background

Each module maps to a well-studied mechanism in human perception:

| Module | Neuroscience analog | Key paper |
|--------|-------------------|-----------|
| HabituationFilter | Stimulus-specific adaptation (SSA) | Thompson & Spencer, 1966 |
| CircadianRhythm | SCN / cortisol-melatonin cycle | Borbely, 1982 |
| DecisionEngine | Salience network / dorsal attention | Corbetta & Shulman, 2002 |
| NotificationQueue | Orienting response (Sokolov) | Sokolov, 1963 |
| Scheduler | Ultradian rhythms | Kleitman, 1963 |
| BaseSource | Sensory transduction | — |
| TimestampLog | Episodic memory encoding | Tulving, 1972 |

Cortex is designed as the **perception layer** in a three-layer agent architecture:

1. **Perception** (Cortex) — filter, prioritize, schedule
2. **Memory** (Cognee, LangChain, etc.) — store, retrieve, reason
3. **Action** (ReachyMini, APIs, etc.) — execute in the world

## License

MIT
