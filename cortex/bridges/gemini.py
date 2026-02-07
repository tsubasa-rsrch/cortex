"""Cortex-Gemini 3 Bridge.

Connects Cortex perception to Google Gemini 3 for cognitive reasoning.
Cortex filters sensor noise, Gemini 3 reasons about what matters.

Architecture:
    Physical World → Cortex (filter/prioritize) → Gemini 3 (reason/plan)
                                                  → Actions (respond/alert)

The key insight: most AI agents send everything to the LLM.
Cortex filters first, so Gemini 3 only reasons about novel, important events.
This saves API calls, reduces latency, and mimics how human cognition works:
unconscious filtering (Cortex) + conscious reasoning (Gemini 3).

Usage:
    from cortex.bridges.gemini import CortexGeminiBridge

    bridge = CortexGeminiBridge(api_key="your-gemini-api-key")

    # Process events through perception + reasoning pipeline
    result = bridge.perceive_and_reason(events)

    # Get a reasoned response about what's happening
    response = bridge.reason_about_context("What should I do?")
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..sources.base import Event, BaseSource
from ..habituation import HabituationFilter
from ..circadian import CircadianRhythm
from ..decision import DecisionEngine, Action
from ..notifications import NotificationQueue
from ..scheduler import Scheduler


@dataclass
class GeminiConfig:
    """Gemini 3 API configuration."""
    api_key: str = ""
    model: str = "gemini-3-flash-preview"
    mock_mode: bool = True
    max_tokens: int = 1024
    temperature: float = 0.7
    api_base: str = "https://generativelanguage.googleapis.com/v1beta"


@dataclass
class ReasoningResult:
    """Result from Gemini 3 reasoning about perceived events."""
    reasoning: str
    action: str
    confidence: float
    events_analyzed: int
    model: str
    latency_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CortexGeminiBridge:
    """Bridge between Cortex perception and Gemini 3 reasoning.

    Cortex handles the "what to pay attention to" (perception).
    Gemini 3 handles the "what to do about it" (reasoning).

    Like the human brain:
    - Cortex = thalamus + sensory cortex (filtering, habituation)
    - Gemini 3 = prefrontal cortex (reasoning, planning, decisions)

    Integration points:
    1. HabituationFilter → Pre-filter: Only novel events reach Gemini 3
    2. CircadianRhythm → Context: Time-of-day awareness for reasoning
    3. DecisionEngine → Priority: Which events need deep reasoning
    4. NotificationQueue → History: Recent context for reasoning
    5. Scheduler → Periodic: Scheduled reasoning tasks
    """

    def __init__(self, gemini_config: Optional[GeminiConfig] = None):
        self.gemini_config = gemini_config or GeminiConfig()

        # Cortex modules (perception layer)
        self.habituation = HabituationFilter()
        self.circadian = CircadianRhythm()
        self.circadian.check_and_update()
        self.decision = DecisionEngine()
        self.notifications = NotificationQueue()
        self.scheduler = Scheduler()

        # State
        self._reasoning_history: List[ReasoningResult] = []
        self._perceived_events: List[Event] = []
        self._api_calls = 0
        self._events_filtered = 0

        # Register periodic tasks
        self.scheduler.register(
            "context_summary", 300,  # Every 5 minutes
            self._generate_periodic_summary
        )

    def perceive(self, events: List[Event]) -> List[Event]:
        """Apply Cortex perception filters to events.

        Returns only events that pass habituation and priority filters.
        This is where we save API calls - most events get filtered here.
        """
        passed = []
        for event in events:
            value = event.priority
            if event.raw_data:
                value = event.raw_data.get('diff', event.raw_data.get('volume', event.priority))

            should_alert, reason = self.habituation.should_notify(event.source, value)
            if should_alert:
                passed.append(event)
                self._perceived_events.append(event)
            else:
                self._events_filtered += 1

        return passed

    def reason(self, prompt: str, context: Optional[Dict] = None) -> ReasoningResult:
        """Send a reasoning request to Gemini 3.

        Includes Cortex perception context automatically.
        """
        # Build context from Cortex state
        perception_context = self._build_perception_context()
        if context:
            perception_context.update(context)

        # Build the full prompt with perception context
        full_prompt = self._build_reasoning_prompt(prompt, perception_context)

        # Call Gemini 3 API
        start_time = time.time()
        response = self._call_gemini(full_prompt)
        latency = (time.time() - start_time) * 1000

        result = ReasoningResult(
            reasoning=response.get("reasoning", ""),
            action=response.get("action", "observe"),
            confidence=response.get("confidence", 0.5),
            events_analyzed=len(self._perceived_events),
            model=self.gemini_config.model,
            latency_ms=latency,
        )

        self._reasoning_history.append(result)
        self._api_calls += 1
        return result

    def perceive_and_reason(self, events: List[Event]) -> Optional[ReasoningResult]:
        """Full pipeline: filter events through Cortex, then reason with Gemini 3.

        This is the main entry point. Returns None if no events pass filters.
        """
        # Step 1: Cortex perception (filter noise)
        novel_events = self.perceive(events)
        if not novel_events:
            return None

        # Step 2: Decision engine (should we reason about this?)
        action = self.decision.decide(novel_events)

        # Step 3: Build event summary for Gemini 3
        event_summary = self._summarize_events(novel_events)

        # Step 4: Reason with Gemini 3
        prompt = (
            f"You are a cognitive agent. Analyze these sensor events and decide "
            f"the best course of action.\n\n"
            f"Events:\n{event_summary}\n\n"
            f"Initial assessment from rule engine: {action.name} - {action.description}\n\n"
            f"Provide your reasoning and recommended action."
        )

        result = self.reason(prompt)

        # Step 5: Push to notification queue
        priority = "urgent" if result.confidence > 0.8 else "normal"
        self.notifications.push(
            "gemini_reasoning",
            f"[Gemini 3] {result.action}: {result.reasoning[:100]}",
            priority
        )

        return result

    def reason_about_context(self, question: str) -> ReasoningResult:
        """Ask Gemini 3 a question with full Cortex context.

        Useful for interactive queries like "What's happening right now?"
        """
        return self.reason(question)

    def _build_perception_context(self) -> Dict[str, Any]:
        """Build current perception context from Cortex modules."""
        circadian = self.circadian.check_and_update()
        cfg = circadian["config"]
        suggestions = self.circadian.get_current_suggestions()
        unread = self.notifications.get_unread()

        recent = self._perceived_events[-10:] if self._perceived_events else []

        return {
            "time_mode": cfg.get("name", circadian["mode"].value),
            "energy_level": cfg.get("energy_level", "unknown"),
            "suggestions": [
                s.get("message", str(s)) if isinstance(s, dict) else str(s)
                for s in suggestions[:3]
            ],
            "unread_alerts": len(unread),
            "recent_events": [
                {
                    "source": e.source,
                    "type": e.type,
                    "content": e.content,
                    "priority": e.priority,
                }
                for e in recent
            ],
            "events_filtered_count": self._events_filtered,
            "api_calls_made": self._api_calls,
        }

    def _build_reasoning_prompt(self, user_prompt: str, context: Dict) -> str:
        """Build a full prompt with perception context for Gemini 3."""
        mode = context.get("time_mode", "unknown")
        energy = context.get("energy_level", "unknown")
        suggestions = context.get("suggestions", [])
        recent = context.get("recent_events", [])
        filtered = context.get("events_filtered_count", 0)

        events_text = ""
        if recent:
            events_text = "\n".join(
                f"  - [{e['source']}] {e['type']}: {e['content']} (priority: {e['priority']})"
                for e in recent
            )
        else:
            events_text = "  No recent events."

        return f"""## Cortex Perception Context
- Time mode: {mode} (energy: {energy})
- Circadian suggestions: {', '.join(suggestions) if suggestions else 'none'}
- Events filtered (noise removed): {filtered}
- Recent perceived events:
{events_text}

## Your Task
{user_prompt}

Respond in JSON format:
{{"reasoning": "your step-by-step reasoning", "action": "recommended_action", "confidence": 0.0-1.0}}
"""

    def _summarize_events(self, events: List[Event]) -> str:
        """Create a natural language summary of events for reasoning."""
        lines = []
        for e in events:
            lines.append(f"- [{e.source}] {e.type}: {e.content} (priority: {e.priority})")
        return "\n".join(lines)

    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini 3 API. Uses mock mode if no API key."""
        if self.gemini_config.mock_mode:
            return self._mock_gemini_response(prompt)

        return self._real_gemini_call(prompt)

    def _real_gemini_call(self, prompt: str) -> Dict[str, Any]:
        """Make a real API call to Gemini 3."""
        try:
            import urllib.request
            import ssl

            url = (
                f"{self.gemini_config.api_base}/models/"
                f"{self.gemini_config.model}:generateContent"
                f"?key={self.gemini_config.api_key}"
            )

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": self.gemini_config.temperature,
                    "maxOutputTokens": self.gemini_config.max_tokens,
                },
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                result = json.loads(resp.read())
                text = (
                    result.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )

                # Try to parse JSON response (strip markdown fences)
                clean = text.strip()
                if clean.startswith("```"):
                    # Remove ```json ... ``` wrapping
                    lines = clean.split("\n")
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    clean = "\n".join(lines)
                try:
                    parsed = json.loads(clean)
                    return parsed
                except json.JSONDecodeError:
                    return {
                        "reasoning": text,
                        "action": "observe",
                        "confidence": 0.5,
                    }

        except Exception as e:
            self.notifications.push(
                "error", f"Gemini API failed: {e}", "urgent"
            )
            return {
                "reasoning": f"API error: {e}",
                "action": "fallback",
                "confidence": 0.0,
            }

    def _mock_gemini_response(self, prompt: str) -> Dict[str, Any]:
        """Generate a mock Gemini 3 response for testing."""
        # Extract event info from prompt
        has_urgent = "priority: 8" in prompt or "priority: 9" in prompt or "priority: 10" in prompt
        has_motion = "motion" in prompt.lower()
        has_audio = "audio" in prompt.lower() or "speech" in prompt.lower()
        is_night = "night" in prompt.lower() or "Late Night" in prompt

        if has_urgent and is_night:
            return {
                "reasoning": (
                    "High-priority event detected during night hours. "
                    "Night mode heightens vigilance for unusual activity. "
                    "The combination of high priority and unusual timing "
                    "warrants immediate investigation."
                ),
                "action": "alert_and_investigate",
                "confidence": 0.92,
            }
        elif has_urgent:
            return {
                "reasoning": (
                    "High-priority event detected. The habituation filter "
                    "confirmed this is novel (not a repeated stimulus). "
                    "Recommending investigation based on event priority "
                    "and novelty assessment."
                ),
                "action": "investigate",
                "confidence": 0.85,
            }
        elif has_motion and has_audio:
            return {
                "reasoning": (
                    "Multiple sensor modalities detected activity "
                    "(motion + audio). Cross-modal correlation increases "
                    "confidence that this is a real event, not sensor noise. "
                    "Monitoring recommended."
                ),
                "action": "monitor",
                "confidence": 0.75,
            }
        elif has_motion:
            return {
                "reasoning": (
                    "Motion detected by single sensor. Could be a person, "
                    "animal, or environmental factor. Cortex habituation "
                    "filter confirmed novelty. Logging for pattern analysis."
                ),
                "action": "log_and_observe",
                "confidence": 0.6,
            }
        else:
            return {
                "reasoning": (
                    "Events within normal parameters. Cortex perception "
                    "layer has already filtered routine noise. Continuing "
                    "standard monitoring."
                ),
                "action": "continue_monitoring",
                "confidence": 0.5,
            }

    def _generate_periodic_summary(self):
        """Generate periodic reasoning summary (called by Scheduler)."""
        if not self._perceived_events:
            return

        recent = self._perceived_events[-20:]
        event_types = {}
        for e in recent:
            t = e.type
            event_types[t] = event_types.get(t, 0) + 1

        summary = ", ".join(f"{c}x {t}" for t, c in event_types.items())
        self.notifications.push(
            "periodic_summary",
            f"Last 5min: {summary}. {self._events_filtered} events filtered.",
            "low"
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "api_calls": self._api_calls,
            "events_perceived": len(self._perceived_events),
            "events_filtered": self._events_filtered,
            "filter_rate": (
                f"{self._events_filtered / (len(self._perceived_events) + self._events_filtered) * 100:.1f}%"
                if (len(self._perceived_events) + self._events_filtered) > 0
                else "N/A"
            ),
            "reasoning_history": len(self._reasoning_history),
            "mock_mode": self.gemini_config.mock_mode,
            "model": self.gemini_config.model,
            "circadian_mode": self.circadian.current_mode.value,
        }
