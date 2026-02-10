# Demo Recording Guide for Kana
## Next Byte Hacks / Cosmos Cookoff

### Setup
- Screen recording tool: QuickTime Player or OBS
- Terminal: iTerm2 or Terminal.app, dark theme, large font (16pt+)
- Resolution: 1920x1080

### Recording Steps (3 minutes total)

#### Scene 1: The Problem (30 sec)
```bash
# Show raw event count
wc -l ~/.tsubasa-daemon/memory/event_log.jsonl
# Expected: ~3004 lines

# Show a few raw events scrolling fast
tail -20 ~/.tsubasa-daemon/memory/event_log.jsonl | python3 -m json.tool | head -40
```
**Narration**: "A home security system generates thousands of motion events. Most AI agents try to process ALL of them."

#### Scene 2: Architecture (45 sec)
```bash
# Open the architecture diagram
open examples/architecture_diagram.png
```
**Narration**: "Cortex sits between sensors and your reasoning layer, applying neuroscience-inspired filtering."

#### Scene 3: Cortex Replay Demo (60 sec)
```bash
cd ~/Documents/TsubasaWorkspace/cortex
cortex-replay
```
Wait for it to complete (~10 seconds). Color-coded output:
- Green: events that passed the filter (conscious)
- Red: filtered out (habituated)
- Yellow: orienting responses (novel stimuli breaking through)

**Narration**: "3,004 events in, 219 out. 92% noise reduction. The filter learns what's routine and only alerts on novel events."

#### Scene 4: VLM Inference (30 sec)
```bash
# Make sure llama-server is running on port 8090
python3 examples/egocentric_reachy_pipeline.py --demo
```
**Narration**: "When a novel event does trigger, we use local VLM inference for egocentric reasoning. 'I see a person approaching.' Not 'the camera shows.'"

#### Scene 5: Tests & Stats (15 sec)
```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tail -10
```
**Narration**: "201 tests, 8,773 lines of Python, zero external dependencies. pip install cortex-agent."

### Tips
- Keep terminal scrolling visible (shows activity)
- Pause briefly on the replay summary stats
- The VLM inference takes ~2-3 seconds per image, good for dramatic pause
- End with GitHub URL visible: github.com/tsubasa-rsrch/cortex
