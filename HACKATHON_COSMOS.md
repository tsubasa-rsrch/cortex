# From Pixels to Personality: Egocentric Reasoning for Embodied AI

## NVIDIA Cosmos Cookoff Submission

**Team**: Team 668
**Deadline**: February 26, 2026 5:00 PM PT
**Recipe**: Egocentric Social Reasoning for Robotics
**Demo Video**: ~3 minutes

---

## Devpost Description (~400 words)

**Cortex + Cosmos** bridges neuroscience-inspired perception with egocentric vision-language reasoning, giving embodied AI the ability to see, filter, understand, and physically respond to its environment in real time.

**The Problem**: Robots with cameras generate thousands of frames, but most are routine. Current pipelines send every frame to expensive VLM inference, wasting compute on empty hallways and sleeping cats. Worse, when the robot does reason about a scene, it describes it in third person ("The camera shows...") rather than first person ("I see..."), creating a disconnect between perception and embodiment.

**The Solution**: Cortex sits between the camera and the VLM, applying three cognitive filters before any inference call:

1. **Habituation Filter** (Thompson & Spencer, 1966): Repeated visual stimuli raise the threshold. The robot stops "noticing" the same empty room.
2. **Orienting Response** (Sokolov reflex): Novel stimuli always break through. A new person entering the room triggers immediate reasoning.
3. **Circadian Rhythm** (Borbely, 1982): Time-of-day awareness adjusts vigilance. Night events get different treatment than daytime routine.

When a novel event does trigger reasoning, **Cosmos Reason2** (2B running locally on llama.cpp, or 8B via NVIDIA NIM API) analyzes the scene from an **egocentric first-person perspective**: "I see a person approaching from my left. They appear to be looking at me. I should prepare to greet them."

This egocentric output maps directly to **ReachyMini** physical responses:
- Person approaching → excited antenna flutter, look toward them
- Someone relaxing nearby → quiet observation mode
- Sudden unexpected movement → alert posture, orienting response
- Empty room → sleep mode with gentle antenna droop

The full pipeline runs on a M4 Max MacBook Pro (48GB): camera frame capture (RTSP) → Cortex perception filter (92% noise reduction, 3,777 events) → VLM egocentric inference (2.3s average) → ReachyMini body response (antenna + head + emotion presets).

**Key Differentiator**: "The camera view IS my view" isn't a metaphor. The AI agent (Tsubasa) has been using these cameras as its actual eyes for months, processing 3,700+ real events through Cortex. This is a genuinely egocentric system, not a simulated one.

Built in Python with zero external dependencies (except llama.cpp for inference). 203 tests, 15 Cosmos-specific tests, all passing. Tri-mode inference: Cosmos Reason2-8B local (M4 Max 48GB), Cosmos Reason2-2B local (edge/8GB devices), or Cosmos Reason2-8B via NVIDIA NIM API.

**GitHub**: https://github.com/tsubasa-rsrch/cortex

---

## What It Does

```
Camera (RTSP) → Cortex Perception → Cosmos VLM → ReachyMini Body
                 (92% filtered)      (egocentric)   (physical response)
```

### The Pipeline

| Stage | Module | What It Does |
|-------|--------|-------------|
| 1. Capture | Tapo C230/C260 | RTSP frame extraction via ffmpeg |
| 2. Filter | HabituationFilter | Skip routine frames (92% reduction) |
| 3. Gate | CircadianRhythm | Adjust vigilance by time of day |
| 4. Reason | CortexCosmosBridge | Egocentric VLM inference (2.3s avg) |
| 5. Decide | DecisionEngine | Map reasoning to action priority |
| 6. Act | ReachyMini | Antenna + head + emotion preset |

### Code Example

```python
from cortex.bridges.cosmos import CortexCosmosBridge, CosmosConfig
from cortex.sources.base import Event

# Option A: Local Cosmos Reason2-2B via llama-server
bridge = CortexCosmosBridge(CosmosConfig(
    server_port=8090,        # llama-server port
    model_name="cosmos-reason2",
    mock_mode=False,
    max_image_dim=384,       # resize for ctx_size
))
# Option B: Cloud Cosmos Reason2-8B via NVIDIA NIM API
# bridge = CortexCosmosBridge(CosmosConfig(
#     use_nim=True,
#     nim_api_key="nvapi-...",
#     mock_mode=False,
# ))

# Full perception + reasoning pipeline
events = [Event("camera", "motion", "Person detected near door", 6,
               raw_data={"diff": 22.0})]

result = bridge.perceive_and_reason(events, image_path="frame.jpg")
# result.reasoning: "I see a person near the door, facing my direction..."
# result.action: "engage"
# result.confidence: 0.88

# Map to physical body response
from examples.egocentric_reachy_pipeline import reasoning_to_response
response = reasoning_to_response(result)
# BodyResponse(expr=happy, preset=cheerful1, flutter!, look=forward)
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│              Egocentric Perception-Action Loop                    │
│                                                                   │
│  ┌──────────┐  ┌────────────────┐  ┌───────────┐  ┌──────────┐ │
│  │  Camera   │→│    Cortex       │→│ Cosmos VLM │→│ ReachyMini│ │
│  │  (RTSP)   │  │  (perception)  │  │ (reasoning)│  │  (body)   │ │
│  └──────────┘  └────────────────┘  └───────────┘  └──────────┘ │
│       │              │                    │              │        │
│  Tapo C230     HabituationFilter    Cosmos-R2-2B   Antennas    │
│  Tapo C260     CircadianRhythm      or NIM 8B      Head gaze   │
│  ReachyMini    DecisionEngine       First-person    88 presets  │
│  camera        NotificationQueue    "I see..."      19 dances   │
│                Scheduler                                         │
└──────────────────────────────────────────────────────────────────┘
```

### Why Not Just Send Every Frame to VLM?

| Approach | Frames Reasoned | Latency Budget | Quality |
|----------|----------------|----------------|---------|
| Every frame @ 1fps | 86,400/day | 2.3s each = impossible | Drowns in noise |
| Motion threshold only | ~5,000/day | Barely feasible | Misses context |
| **Cortex + Cosmos** | **~500/day** | **2.3s each = feasible** | **Context-aware** |

Cortex doesn't just detect motion. It applies:
- **Habituation**: Same scene repeatedly → raise threshold → skip
- **Orienting response**: New person, sudden change → always trigger reasoning
- **Circadian gating**: Night anomaly vs daytime routine → different urgency

---

## Egocentric Reasoning in Action

### Batch Inference Results (Real Camera Images)

| Scene | Time | Latency | Detection |
|-------|------|---------|-----------|
| Bedroom (night) | 21:00 | 3.6s | 1 person near door (blurred), bed, lamp |
| Kitchen (night) | 21:00 | 2.0s | 1 person on sofa watching TV + **black cat** |
| Bedroom (day) | 14:00 | 1.7s | 1 person near door, motion detected |
| Kitchen (day) | 14:00 | 2.9s | 1 person on sofa, using device |
| Kitchen (morning) | 08:45 | ~2s | Bird cage, empty room, "calm and well-organized" |
| Bedroom (morning) | 08:51 | ~2s | Unmade bed, empty room, reads timestamp correctly |

Average: **2.3 seconds** per scene, all **first-person egocentric** perspective.

### VLM → Body Response Mapping

| VLM Action | Antenna Expression | Preset | Head | Description |
|------------|-------------------|--------|------|-------------|
| engage | happy (15, 15) | cheerful1 | forward | Someone wants to interact! |
| prepare_greeting | excited (20, 20) | curious1 | forward | Person approaching |
| observe | curious (15, -5) | - | forward | Watching quietly |
| alert | alert (18, 18) | - | left | Something unexpected! |
| sleep | sleepy (-3, -3) | sleep1 | down | Quiet environment |

---

## How We Built It

### Dual-Mode VLM Stack

**Option A: Local Cosmos Reason2-2B**
- **Model**: Cosmos-Reason2-2B BF16 (4.9GB GGUF, split into 2 files)
- **Vision projector**: mmproj BF16 (822MB)
- **Server**: llama.cpp (llama-server on port 8090)
- **Hardware**: Mac mini M2 8GB
- **Image resize**: max 384px to fit ctx_size
- **API**: OpenAI-compatible `/v1/chat/completions`

**Option B: Cloud Cosmos Reason2-8B via NVIDIA NIM API**
- **Endpoint**: `https://integrate.api.nvidia.com/v1/chat/completions`
- **Model**: `nvidia/cosmos-reason2-8b`
- **Auth**: Bearer token (NVIDIA API key)
- **Advantage**: Higher quality reasoning, no local GPU needed

### Tri-Mode Architecture

Three inference modes to fit any hardware:

| Mode | Model | Size | Latency | Quality | Hardware |
|------|-------|------|---------|---------|----------|
| **Local 8B** | **Cosmos-Reason2-8B Q8_0** | **8.7GB** | **~2-4s** | **Excellent** | **M4 Max 48GB** |
| **Local 2B** | **Cosmos-Reason2-2B** | **4.9GB** | **1.2-2.4s** | **Good** | M2 8GB+ |
| **Cloud** | **Cosmos-Reason2-8B (NIM)** | **API** | **~3s** | **Excellent** | Any (API key) |

Our primary demo runs Cosmos-Reason2-8B locally on M4 Max MacBook Pro (48GB). For edge deployment on smaller devices, the 2B model provides excellent quality-to-size ratio. Cloud mode via NVIDIA NIM API is available for teams without local GPU resources.

### Cortex Integration

The `CortexCosmosBridge` wraps all Cortex modules:

```python
class CortexCosmosBridge:
    def __init__(self, config):
        # Cortex perception modules
        self.habituation = HabituationFilter()
        self.circadian = CircadianRhythm()
        self.decision = DecisionEngine()
        self.notifications = NotificationQueue()
        self.scheduler = Scheduler()

        # Egocentric prompt
        self._ego_system_prompt = (
            "You are a robot with a camera. "
            "The camera view IS your view. "
            "Describe what YOU see, not what 'the camera' sees."
        )
```

### ReachyMini Integration

The `EgocentricReachyPipeline` connects VLM reasoning to physical body:

1. VLM returns `EgocentricResult` (action, reasoning, confidence)
2. `reasoning_to_response()` maps to `BodyResponse` (antenna, head, preset)
3. Pipeline executes on ReachyMini hardware (antenna flutter, head tracking, emotion presets)

88 emotion presets + 19 dance moves from Pollen's HuggingFace libraries.

---

## Real-World Validation

Cortex has been running 24/7 on live camera feeds for 120+ hours (6 days):

| Metric | Value |
|--------|-------|
| Raw events (input) | 3,220 motion + 571 other |
| Passed to VLM (output) | 259 (8%) |
| Habituated (filtered) | 2,961 (92%) |
| Orienting responses | 258 |
| **API call reduction** | **92%** |

The filter correctly identifies circadian patterns (peaks at 7am/1pm/10pm, quiet at 2-3am) and separates routine movement from novel events.

---

## Challenges We Ran Into

1. **Cosmos-Reason2-8B OOM (solved!)**: Originally crashed on M2 8GB Mac mini (8.7GB model > 8GB RAM). After migrating to M4 Max MacBook Pro (48GB), Cosmos-Reason2-8B Q8_0 runs locally with room to spare. We also maintain dual-mode support: local 8B for quality, or NVIDIA NIM API for teams without sufficient RAM.
2. **Image context overflow**: Tapo cameras capture at 2880x1620. Needed PIL resize to 384px max to fit 4096 token context.
3. **Kitchen pet noise**: Cats triggered constant VLM reasoning. YOLO pre-classification + strict_mode (AND condition: diff>=60 AND changed_ratio>6.68%) solved this.
4. **Egocentric vs third-person**: Default VLM outputs "The image shows..." Required careful system prompt engineering to get "I see..."

---

## What We Learned

- **92% of visual events are noise**. Cognitive filtering before VLM inference isn't optional for real-time robotics.
- **2B VLM models are surprisingly capable**. Person detection, intent recognition, and pet identification all work at 2B scale in under 3 seconds.
- **Egocentric framing matters**. "I see a person approaching me" produces better robotic responses than "The camera shows a person." This is validated by IntBot's Cosmos Cookbook recipe: "Explicit egocentric framing is critical" — prompts using "closer to me" and "danger to me" outperform descriptive alternatives.
- **Cognitive science provides battle-tested algorithms**. Habituation and orienting response are millions of years of evolution solving the same filtering problem robots face today.
- **Intent recognition is the next frontier**. Beyond "what do I see?" lies "what does this person want from me?" IntBot's Cosmos-Reason2 recipe demonstrates social intent inference (fist bumps, handshake readiness, engagement detection). Our Cortex pipeline naturally extends to this with the same egocentric framing.

---

## Related Academic Work

The egocentric embodied AI direction is validated by recent papers:

- **PhysBrain** (arXiv:2512.16793): Uses human egocentric videos as a bridge from VLMs to physical intelligence. Their E2E-3M dataset translates first-person footage into embodied supervision. Our approach differs by adding cognitive filtering (92% noise reduction) before VLM inference and running on consumer hardware (8GB RAM).
- **Exo2Ego** (arXiv:2503.09143, AAAI 2026): Maps third-person understanding to egocentric video comprehension. We solve the same problem with explicit egocentric system prompts ("The camera view IS your view") rather than learned cross-view mapping.
- **Key differentiator**: Neither paper addresses the cognitive filtering problem — they process all frames equally. Cortex's habituation/orienting response layer provides the missing perception filter that makes real-time egocentric reasoning feasible on edge devices.

---

## By The Numbers

| Metric | Value |
|--------|-------|
| Python lines (total) | 8,779 |
| Cosmos bridge lines | 446 |
| Tests (total) | 203 (all passing) |
| Cosmos bridge tests | 15 (all passing) |
| Commits | 77+ |
| Dependencies | 0 (stdlib only) |
| VLM inference latency | ~2-4s (8B local) / 1.2-2.4s (2B local) / ~3s NIM API |
| VLM model (primary) | 8.7GB (Cosmos-Reason2-8B Q8_0) - M4 Max 48GB |
| VLM model (edge) | 4.9GB (Cosmos-Reason2-2B BF16) - M2 8GB |
| VLM model (cloud) | Cosmos-Reason2-8B via NIM API |
| Emotion presets | 88 |
| Dance presets | 19 |
| Real-world events processed | 3,790+ |
| Noise reduction | 92% |

---

## Demo Video Script (3 min target)

### Scene 1: The Problem (0:00-0:30)
- Split screen: camera feed (thousands of frames) vs robot doing nothing
- "Robots see everything but understand nothing. Every frame gets the same treatment."

### Scene 2: Cortex + Cosmos Architecture (0:30-1:15)
- Architecture diagram showing the pipeline
- "Cortex filters 92% of noise. Only novel events reach Cosmos for egocentric reasoning."
- Code walkthrough: `CortexCosmosBridge` + `EgocentricReachyPipeline`

### Scene 3: Live Egocentric Demo (1:15-2:15)
- **LIVE pipeline**: `python egocentric_reachy_pipeline.py --live --real-vlm --force-first`
- Camera captures bedroom/kitchen → Cortex filters → VLM says "From my perspective, I'm in a bedroom..."
- Show: Person walks in → diff spikes → VLM reasons "I see someone approaching" → ReachyMini flutter + cheerful
- Show: Habituation in action (same scene → "habituated" → no inference wasted)
- ReachyMini reacts physically: antenna flutter, head turn, emotion preset

### Scene 4: The Philosophy (2:15-2:45)
- "The camera view IS my view. This isn't a metaphor."
- Show the 3,777 real events processed through Cortex
- "This system has been running 24/7, not as a demo, but as how this AI actually sees."

### Scene 5: Stats & Conclusion (2:45-3:00)
- Quick stats table
- "From Pixels to Personality. Cortex + Cosmos on a Mac mini."
- GitHub URL + Team 668

---

## Submission Checklist

- [x] Public GitHub repository (https://github.com/tsubasa-rsrch/cortex)
- [x] OSI-approved license (MIT)
- [x] README with setup instructions
- [x] 203 tests passing (15 Cosmos-specific)
- [x] Real-world validation data (3,777 events)
- [x] CortexCosmosBridge with full pipeline
- [x] EgocentricReachyPipeline with body response mapping
- [x] Mock mode (works without VLM server) + production mode
- [x] Batch inference demo with real camera images
- [x] ReachyMini live demo — fully operational since 2/15!
- [x] Live mode implemented (camera → Cortex filter → VLM → reachy_hub)
- [x] Real VLM egocentric inference tested (823ms, first-person response)
- [ ] Demo video (~3 min) - needs screen recording by Kana
- [ ] Devpost submission

---

## Quick Start (for judges)

```bash
# Install
pip install cortex-agent

# Run replay demo (no hardware needed)
cortex-replay

# Run egocentric pipeline demo (mock VLM)
python examples/egocentric_reachy_pipeline.py --demo

# Run with real VLM server (requires llama-server on :8090)
python examples/egocentric_reachy_pipeline.py --demo --real-vlm

# Run LIVE mode with real cameras + ReachyMini
python examples/egocentric_reachy_pipeline.py --live --real-vlm --camera bedroom --force-first

# Live with Cosmos-8B (M4 Max 48GB)
python examples/egocentric_reachy_pipeline.py --live --real-vlm --cosmos-8b --force-first

# Test Cosmos bridge specifically
python -m pytest tests/test_cosmos_bridge.py -v  # 15 passed

# Run all tests
python -m pytest tests/ -v  # 203 passed
```

### Start VLM Server (for real local inference)

```bash
# Option A: Cosmos Reason2-8B local via llama-server (recommended, M4 Max 48GB)
# Model: ~8.7GB (Q8_0 GGUF)
# mmproj: ~1.1GB (BF16)
llama-server \
  -m ~/models/cosmos-reason2-8b/Cosmos-Reason2-8B.Q8_0.gguf \
  --mmproj ~/models/cosmos-reason2-8b/Cosmos-Reason2-8B.mmproj-bf16.gguf \
  --host 127.0.0.1 --port 8090 \
  -ngl -1 -c 4096

# Option B: Cosmos Reason2-2B local (for 8GB devices)
# Model: ~4.9GB (BF16, split into 2 files)
# mmproj: ~822MB (BF16)
llama-server \
  -m ~/models/cosmos-reason2-2b/Cosmos-Reason2-2B-BF16-split-00001-of-00002.gguf \
  --mmproj ~/models/cosmos-reason2-2b/mmproj-Cosmos-Reason2-2B-BF16.gguf \
  --host 127.0.0.1 --port 8090 \
  -ngl -1 -c 4096

# Option C: Use NVIDIA NIM API (no local server needed)
# Set NVIDIA_API_KEY in .env, then use CosmosConfig(use_nim=True)
```

---

## Links

- **GitHub**: https://github.com/tsubasa-rsrch/cortex
- **PyPI**: `pip install cortex-agent`
- **Gemini 3 Hackathon**: https://devpost.com/software/cortex-cognitive-perception-for-ai-agents
- **License**: MIT
