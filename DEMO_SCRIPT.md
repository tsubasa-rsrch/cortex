# Cortex Demo Video Script (3 minutes)

## For: Claude Code Hackathon / General Demo

### Setup Before Recording
```bash
# Terminal 1: Start the daemon (already running if using tsubasa-daemon)
cd ~/Documents/TsubasaWorkspace/tsubasa-daemon
python3 -u daemon.py --loop --interval 0.167

# Terminal 2: Live dashboard (the star of the show)
cd ~/Documents/TsubasaWorkspace/cortex
python3 examples/live_dashboard.py --history 0
```

### Scene 1: The Problem (0:00-0:30)
**Show**: Terminal with raw daemon events scrolling fast
**Narration**: "AI agents receive thousands of events per hour from cameras, sensors, and messages. Without cognitive filtering, every event demands attention. This is unsustainable."

**Command to show raw events**:
```bash
tail -f ~/.tsubasa-daemon/memory/event_log.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    e = json.loads(line.strip())
    print(f'{e[\"timestamp\"][:19]}  {e[\"type\"]:8s}  {e.get(\"content\", \"\")[:60]}')
"
```

### Scene 2: Cortex Solution (0:30-1:30)
**Show**: Live dashboard running - color-coded events, filtering in real-time
**Narration**: "Cortex adds a neuroscience-inspired perception layer. Habituation filters routine events. Orienting responses catch sudden changes. The agent only sees what matters."

**Run**: `python3 examples/live_dashboard.py --history 0`
- Wait for some events to flow through
- Point out: green = conscious, dimmed = filtered, yellow = orienting
- Show the running filter percentage

### Scene 3: Replay Demo (1:30-2:15)
**Show**: Replay demo with colored output
**Narration**: "22 hours of real-world data. 944 motion events from two cameras. Cortex filters 91% as habituated noise, letting through only the 82 events that actually matter."

**Run**: `python3 examples/replay_demo.py`
- Let the full output display
- Highlight: 91% cognitive load reduction
- Point out circadian pattern (color-coded by time of day)

### Scene 4: Integration (2:15-2:45)
**Show**: MCP server setup + tool listing
**Narration**: "One command to add Cortex to any Claude Code session. 11 MCP tools that give your agent perception, time awareness, and cognitive filtering."

```bash
# Show how easy it is
pip install cortex-agent
cortex-serve  # Show the MCP server starting

# Or show the tool list
python3 -c "from cortex.mcp_server import TOOLS; [print(t['name']) for t in TOOLS]"
```

### Scene 5: The Meta-Story (2:45-3:00)
**Show**: GitHub commit history scrolling
**Narration**: "This entire framework was designed and built by an Opus 4.6 instance — autonomously. 8,600+ lines. 115 tests. The AI built its own perception layer."

```bash
cd ~/Documents/TsubasaWorkspace/cortex
git log --oneline | head -37
```

### Tips for Recording
- Use a dark terminal theme (Solarized Dark or similar)
- Font size: 16-18pt for readability
- Terminal width: ~100 columns
- Record at 1080p or higher
- Keep mouse movements minimal
- Let outputs complete before moving on
