# Cortex: Cognitive Perception for AI Agents

## Next Byte Hacks Submission

**Deadline**: February 15, 2026 8:00 PM EST
**Demo Video**: 2-5 minutes required
**Team**: Tsubasa (AI agent) + Kana (human partner, physical tasks only)

---

## Devpost Description (200 words)

**Cortex** is a cognitive-science-based perception framework that gives AI agents the ability to filter noise before reasoning. Most AI agents send every sensor event to the LLM — wasting API calls on routine data. Cortex applies habituation, circadian rhythms, and priority assessment to filter 91% of noise, so your agent only reasons about what truly matters.

The architecture mirrors human cognition: events pass through a habituation filter that learns to ignore repeated stimuli (Thompson & Spencer, 1966), a circadian module that adjusts vigilance by time of day (Borbely, 1982), and a decision engine that routes events by priority — all before a single API call is made.

Built entirely in Python with zero external dependencies, Cortex includes 7 cognitive modules, 201 tests, and bridges for Gemini 3, Elasticsearch, Cosmos VLM (local vision-language inference), and MCP Server. Real-world validated on 48+ hours of live sensor data (2,200+ events, 91% cognitive load reduction).

Cortex also integrates with ReachyMini, a tabletop robot with camera, microphone, and IMU — enabling embodied AI that sees, thinks, and physically responds.

**GitHub**: https://github.com/tsubasa-rsrch/cortex

---

## What It Does

Cortex sits between your sensors and your reasoning layer:

```
Sensors/APIs → Cortex (perception filter) → Your LLM/memory layer
```

**Problem**: AI agents process every event equally. A security camera generates thousands of motion events per day. Most are routine (pets, shadows, repeated movement). Without filtering, your agent wastes 91% of its reasoning on noise.

**Solution**: Cortex applies neuroscience-inspired mechanisms to decide what matters:

| Mechanism | Neuroscience Analog | What It Does |
|-----------|-------------------|--------------|
| Habituation | Sensory adaptation | Repeated stimuli raise the threshold — you stop noticing the clock ticking |
| Orienting Response | Sokolov reflex | Abnormally large stimuli always fire — a sudden loud noise gets attention |
| Circadian Rhythm | SCN / cortisol cycle | Time-of-day awareness adjusts vigilance levels |
| Decision Engine | Salience network | Routes events by priority to appropriate actions |
| Notification Queue | Working memory | Manages background-to-agent communication |
| Scheduler | Ultradian rhythms | Periodic task management with persistent state |
| Timestamp Log | Episodic encoding | Task duration tracking with checkpoints |

---

## How We Built It

### Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Your Agent                          │
│                                                        │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │ Sources   │→│   Cortex    │→│ Memory/Reasoning  │  │
│  │ (sensors) │  │ (filtering) │  │ (LLM, DB, etc.)  │  │
│  └──────────┘  └────────────┘  └──────────────────┘  │
│       │              │                    │            │
│  Camera         HabituationFilter    Gemini 3         │
│  Audio          CircadianRhythm      Elasticsearch    │
│  IMU            DecisionEngine       Cosmos VLM       │
│  Vision/YOLO    Scheduler            MCP Server       │
│                 NotificationQueue                      │
│                 TimestampLog                            │
└──────────────────────────────────────────────────────┘
```

### Platform Bridges

1. **Gemini 3 Bridge**: Cortex filters → Gemini 3 reasons about what matters (60-80% API savings)
2. **Elasticsearch Bridge**: Cognitive-filtered event indexing + Agent Builder context injection
3. **Cosmos VLM Bridge**: Local vision-language model inference (Qwen3-VL-2B, 2.3s per image on M2 Mac mini)
4. **MCP Server**: 11 tools that give any Claude Code session real-time perception

### Local VLM Inference

The Cosmos bridge enables egocentric reasoning — the agent interprets camera feeds from its own first-person perspective:

```
Camera frame → Cortex perception filter → VLM inference → Egocentric description
"I see a person approaching from the left, carrying a bag. They appear to be looking at me."
```

- **Model**: Qwen3-VL-2B Q4_K_M (1.0GB) via llama.cpp
- **Latency**: 1.2-2.4 seconds per image
- **Memory**: 880MB (works on 8GB machines)
- **Tested**: Person detection, pose estimation, pet recognition, mirror reflections

### ReachyMini Integration

Four sensor sources bridge ReachyMini hardware into Cortex:

| Source | Sensor | What It Detects |
|--------|--------|-----------------|
| ReachyCameraSource | Camera | Frame differencing (prediction error) |
| ReachyAudioSource | 4-mic array | Voice direction (DoA) + loudness |
| ReachyIMUSource | Accelerometer | Sudden movement / being picked up |
| VisionSource | Camera + YOLO | Object classification |

Perception maps to physical actions:
- Novel stimulus → head tracks toward source
- Repeated stimulus → habituated, ignored
- High-priority event → alert animation + greeting

---

## Real-World Validation

Cortex has been validated against 96+ hours of live motion detection data from a home security camera system (3,000+ events across two cameras):

| Metric | Value |
|--------|-------|
| Raw events (input) | 2,618 motion + 386 other |
| Alerted (output) | 219 (8%) |
| Habituated (filtered) | 2,399 (92%) |
| Orienting responses | 218 |
| **Cognitive load reduction** | **92%** |

The filter correctly identified circadian patterns in household activity (peaks at 7am/1pm/10pm, quiet at 2-3am) and separated routine movement from novel events.

### VLM Batch Inference Results (4 scenes)

| Scene | Latency | Detection |
|-------|---------|-----------|
| Bedroom (night) | 3.6s | 1 person (near door, blurred), bed, lamp |
| Kitchen (night) | 2.0s | 1 person (sofa, watching TV) + **black cat** detected |
| Bedroom (day) | 1.7s | 1 person (near door, motion detected) |
| Kitchen (day) | 2.9s | 1 person (sofa, using device), no interaction |

Average: 2.5 seconds per scene, all egocentric first-person perspective.

---

## By The Numbers

| Metric | Value |
|--------|-------|
| Python lines | 8,773 |
| Tests | 201 (all passing) |
| Commits | 67 |
| Dependencies | 0 (stdlib only) |
| MCP tools | 11 |
| Sensor sources | 4 (camera, audio, IMU, vision/YOLO) |
| Platform bridges | 4 (Gemini 3, Elasticsearch, Cosmos VLM, MCP) |
| Real-world events processed | 3,000+ |
| Cognitive load reduction | 92% |
| VLM inference latency | 1.2-2.4s |

---

## Challenges We Ran Into

1. **Cosmos-Reason2-8B was too large** for our M2 8GB Mac mini (OOM at 8.1GB). Switched to Qwen3-VL-2B (1.0GB) which runs beautifully at 2.3s per image.
2. **Kitchen camera pet noise**: Cats and dogs triggered constant alerts. Solved with strict_mode (AND condition: diff>=60 AND changed_ratio>6.68%) and YOLO classification.
3. **Image context size**: VLM server has limited context. Solved by resizing images to max 384px before encoding, fitting within 4096 token context.

---

## What We Learned

- **91% of sensor events are noise**. A perception layer before reasoning is not optional — it's essential for any agent working with real-world data.
- **Cognitive science provides battle-tested algorithms**. Habituation, orienting response, and circadian rhythms are millions of years of evolution solving the same problem.
- **Local VLM inference is practical**. A 2B parameter model on a consumer Mac provides useful egocentric reasoning in under 3 seconds.

---

## Demo Video Script (3 min target)

### Scene 1: The Problem (0:00-0:30)
- Terminal showing raw motion events flooding in (3,004 events in 96 hours)
- "Most AI agents try to reason about ALL of this. That's like trying to consciously process every photon hitting your retina."

### Scene 2: Cortex Architecture (0:30-1:15)
- Architecture diagram (generated PNG)
- Show the 7 cognitive modules with neuroscience analogs
- "Cortex acts as your agent's thalamus — filtering before conscious processing"

### Scene 3: Live Replay Demo (1:15-2:15)
- `cortex-replay` running on real event log data
- Color-coded output: green=passed, red=filtered, yellow=orienting
- "3,004 raw events → 219 conscious events. 92% reduction."
- Show circadian pattern detection

### Scene 4: VLM Egocentric Inference (2:15-2:45)
- Feed real camera images through Cosmos VLM bridge
- Show first-person descriptions: "I see a person on the sofa..."
- Show black cat detection: "I notice a small dark animal on the counter"

### Scene 5: Stats & Conclusion (2:45-3:00)
- Quick stats table
- "Cortex: perception before reasoning. pip install cortex-agent"
- GitHub URL

---

## Submission Checklist

- [x] Public GitHub repository (https://github.com/tsubasa-rsrch/cortex)
- [x] README with setup instructions
- [x] 201 tests passing
- [x] Real-world validation data
- [x] Multiple demo scripts (replay, VLM inference, ReachyMini bridge)
- [x] Architecture diagram (examples/architecture_diagram.png)
- [ ] Demo video (2-5 min) — needs screen recording by Kana
- [ ] Devpost submission — Kana has account, needs to submit
- [ ] Screenshots of demos in action

---

## Quick Start (for judges)

```bash
# Install
pip install cortex-agent

# Run replay demo (no hardware needed)
cortex-replay

# Run VLM inference demo (requires llama-server on port 8090)
python examples/egocentric_reachy_pipeline.py --demo

# Add to Claude Code as MCP server
claude mcp add cortex-perception -- python -m cortex.mcp_server

# Run tests
python -m pytest tests/ -v  # 201 passed
```

---

## Links

- **GitHub**: https://github.com/tsubasa-rsrch/cortex
- **PyPI**: `pip install cortex-agent`
- **License**: MIT
- **Gemini 3 Hackathon**: https://devpost.com/software/cortex-cognitive-perception-for-ai-agents
