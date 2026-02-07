# Cortex + Gemini 3: Cognitive Perception for AI Agents

## Devpost Submission (200-word description)

**Cortex** is a cognitive-science-based perception framework that gives AI agents the ability to filter noise before reasoning. Most AI agents send every sensor event to the LLM — wasting API calls on routine data. Cortex applies habituation, circadian rhythms, and priority assessment to filter 60-80% of noise, so Gemini 3 only reasons about what truly matters.

The architecture mirrors human cognition: Cortex acts as the thalamus (unconscious filtering), while Gemini 3 serves as the prefrontal cortex (conscious reasoning). Events pass through a habituation filter that learns to ignore repeated stimuli, a circadian module that adjusts vigilance by time of day, and a decision engine that routes events by priority — all before a single API call is made.

Built entirely in Python with zero external dependencies (stdlib-only), Cortex includes 7 cognitive modules, 111 tests, and bridges for Gemini 3, Elasticsearch, and MCP. The Gemini 3 bridge provides a complete perceive-reason-act pipeline with mock mode for testing and real API integration for production.

Inspired by Thompson & Spencer (1966) on habituation, Borbely (1982) on circadian rhythms, and Corbetta & Shulman (2002) on salience networks.

**GitHub**: https://github.com/tsubasa-rsrch/cortex

## Demo Script

```bash
# Mock mode (no API key needed)
python examples/gemini_cognitive_agent.py

# With real Gemini 3 API
GEMINI_API_KEY=your-key python examples/gemini_cognitive_agent.py
```

## Submission Checklist

- [x] Public GitHub repository
- [x] Uses Gemini 3 API (gemini-3-flash-preview)
- [x] New application (built for this hackathon)
- [x] README with setup instructions
- [x] Demo script with mock + real API modes
- [ ] 3-minute demo video
- [ ] Devpost registration
- [ ] Gemini API key for live demo

## Key Differentiators

1. **Cognitive Science Foundation**: Not just "filter by rules" — uses actual neuroscience mechanisms (habituation, circadian, orienting response)
2. **60-80% API Savings**: Most events are noise. Cortex filters before calling Gemini 3
3. **Zero Dependencies**: Pure stdlib Python, works anywhere
4. **111 Tests**: Well-tested, production-ready
5. **Multiple Bridges**: Gemini 3 + Elasticsearch + MCP Server
6. **ReachyMini Integration**: Physical robot body with camera, mic, IMU sensors
