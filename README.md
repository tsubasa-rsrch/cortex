# Cortex

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

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       Your Agent                              │
│                                                               │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────────────┐ │
│  │ Sources   │→│   Cortex    │→│  Memory / Reasoning       │ │
│  │ (sensors) │  │ (filtering) │  │  (Cognee, LangChain, …)  │ │
│  └──────────┘  └────────────┘  └──────────────────────────┘ │
│       │              │                                        │
│  BaseSource     HabituationFilter         ┌───────────────┐ │
│  Event          CircadianRhythm           │  Body / API    │ │
│  ReachyCamera   Scheduler                 │  (ReachyMini,  │ │
│  ReachyAudio    NotificationQueue         │   Slack, …)    │ │
│  ReachyIMU      TimestampLog              └───────────────┘ │
│                 DecisionEngine                               │
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

63 tests, <0.2s, zero external dependencies.

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
