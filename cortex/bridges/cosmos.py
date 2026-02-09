"""Cortex-Cosmos Reason2 Bridge.

Connects Cortex perception to NVIDIA Cosmos Reason2 for egocentric reasoning.
Cosmos Reason2 runs locally via llama.cpp, no cloud API needed.

Architecture:
    Camera → Cortex (filter/prioritize) → Cosmos Reason2 (egocentric reasoning)
                                         → Actions (respond/alert/embody)

The key insight: Cosmos Reason2 excels at egocentric reasoning - understanding
the world from the camera's (robot's) perspective. Combined with Cortex's
perceptual filtering, only novel visual events trigger reasoning.

"The camera view is my view" - this isn't a metaphor, it's literally true.

Usage:
    from cortex.bridges.cosmos import CortexCosmosBridge, CosmosConfig

    bridge = CortexCosmosBridge(CosmosConfig(
        model_path="/path/to/Cosmos-Reason2-8B.Q8_0.gguf",
        mmproj_path="/path/to/Cosmos-Reason2-8B.mmproj-q8_0.gguf",
    ))

    # Start the local llama-server
    bridge.start_server()

    # Process events with egocentric reasoning
    result = bridge.perceive_and_reason(events, image_path="frame.jpg")

    # Ask egocentric questions
    result = bridge.reason_about_scene("Is anyone looking at me?", "frame.jpg")
"""

import base64
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..sources.base import Event
from ..habituation import HabituationFilter
from ..circadian import CircadianRhythm
from ..decision import DecisionEngine
from ..notifications import NotificationQueue
from ..scheduler import Scheduler


@dataclass
class CosmosConfig:
    """Cosmos Reason2 local inference configuration."""
    model_path: str = ""
    mmproj_path: str = ""
    server_host: str = "127.0.0.1"
    server_port: int = 8090
    mock_mode: bool = True
    max_tokens: int = 1024
    temperature: float = 0.3
    n_gpu_layers: int = -1  # -1 = offload all to Metal
    ctx_size: int = 8192
    model_name: str = "cosmos-reason2-8b"  # or "qwen3-vl-2b" etc.
    max_image_dim: int = 384  # resize images to fit ctx_size


@dataclass
class EgocentricResult:
    """Result from Cosmos Reason2 egocentric reasoning."""
    reasoning: str
    action: str
    confidence: float
    scene_description: str
    events_analyzed: int
    model: str
    latency_ms: float
    has_image: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CortexCosmosBridge:
    """Bridge between Cortex perception and Cosmos Reason2 egocentric reasoning.

    Cortex handles the "what to pay attention to" (perception).
    Cosmos Reason2 handles the "what is happening from my perspective" (egocentric reasoning).

    Like the human brain:
    - Cortex = thalamus + sensory cortex (filtering, habituation)
    - Cosmos = visual cortex + social cognition (scene understanding, intent detection)

    Unique to Cosmos Reason2:
    - Egocentric perspective: "Is this person approaching me?"
    - Physical reasoning: "Will this object collide with me?"
    - Social awareness: "Does anyone want to interact with me?"
    """

    def __init__(self, config: Optional[CosmosConfig] = None):
        self.config = config or CosmosConfig()
        self._server_process: Optional[subprocess.Popen] = None

        # Cortex modules (perception layer)
        self.habituation = HabituationFilter()
        self.circadian = CircadianRhythm()
        self.circadian.check_and_update()
        self.decision = DecisionEngine()
        self.notifications = NotificationQueue()
        self.scheduler = Scheduler()

        # State
        self._reasoning_history: List[EgocentricResult] = []
        self._perceived_events: List[Event] = []
        self._api_calls = 0
        self._events_filtered = 0

        # Egocentric prompt templates
        self._ego_system_prompt = (
            "You are a robot with a camera. The camera view IS your view. "
            "Everything you see is from your first-person perspective. "
            "When asked about the scene, describe what YOU see, not what 'the camera' sees. "
            "You can reason about: who is near you, what they're doing, "
            "whether they want to interact with you, and what actions you should take."
        )

    @property
    def server_url(self) -> str:
        return f"http://{self.config.server_host}:{self.config.server_port}"

    def start_server(self) -> bool:
        """Start the local llama-server with Cosmos Reason2 model."""
        if self.config.mock_mode:
            return True

        if not self.config.model_path or not Path(self.config.model_path).exists():
            self.notifications.push(
                "error", f"Model not found: {self.config.model_path}", "urgent"
            )
            return False

        cmd = [
            "llama-server",
            "-m", self.config.model_path,
            "--host", self.config.server_host,
            "--port", str(self.config.server_port),
            "-ngl", str(self.config.n_gpu_layers),
            "-c", str(self.config.ctx_size),
        ]

        if self.config.mmproj_path and Path(self.config.mmproj_path).exists():
            cmd.extend(["--mmproj", self.config.mmproj_path])

        try:
            self._server_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            # Wait for server to be ready
            time.sleep(5)
            return self._check_server_health()
        except Exception as e:
            self.notifications.push("error", f"Failed to start server: {e}", "urgent")
            return False

    def stop_server(self):
        """Stop the local llama-server."""
        if self._server_process:
            self._server_process.terminate()
            self._server_process.wait(timeout=10)
            self._server_process = None

    def _check_server_health(self) -> bool:
        """Check if llama-server is responding."""
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.server_url}/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return data.get("status") == "ok"
        except Exception:
            return False

    def perceive(self, events: List[Event]) -> List[Event]:
        """Apply Cortex perception filters to events."""
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

    def reason_about_scene(
        self, question: str, image_path: Optional[str] = None
    ) -> EgocentricResult:
        """Ask Cosmos Reason2 about the current scene from egocentric perspective."""
        start_time = time.time()

        # Build messages for OpenAI-compatible API
        messages = [
            {"role": "system", "content": self._ego_system_prompt},
        ]

        user_content: list = []

        # Add image if provided
        has_image = False
        if image_path and Path(image_path).exists():
            img_data = self._encode_image(image_path)
            if img_data:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}
                })
                has_image = True

        user_content.append({"type": "text", "text": question})
        messages.append({"role": "user", "content": user_content})

        # Call local server
        response = self._call_cosmos(messages)
        latency = (time.time() - start_time) * 1000

        result = EgocentricResult(
            reasoning=response.get("reasoning", ""),
            action=response.get("action", "observe"),
            confidence=response.get("confidence", 0.5),
            scene_description=response.get("scene_description", ""),
            events_analyzed=len(self._perceived_events),
            model=self.config.model_name,
            latency_ms=latency,
            has_image=has_image,
        )

        self._reasoning_history.append(result)
        self._api_calls += 1
        return result

    def perceive_and_reason(
        self, events: List[Event], image_path: Optional[str] = None
    ) -> Optional[EgocentricResult]:
        """Full pipeline: filter events, then egocentric reasoning with Cosmos."""
        # Step 1: Cortex perception
        novel_events = self.perceive(events)
        if not novel_events:
            return None

        # Step 2: Decision engine
        action = self.decision.decide(novel_events)

        # Step 3: Build egocentric prompt
        event_summary = self._summarize_events(novel_events)
        prompt = (
            f"I just detected these events from my sensors:\n{event_summary}\n\n"
            f"Looking at what's in front of me right now, "
            f"what is happening? Is anyone interacting with me? "
            f"What should I do?"
        )

        # Step 4: Egocentric reasoning
        result = self.reason_about_scene(prompt, image_path)

        # Step 5: Push notification
        priority = "urgent" if result.confidence > 0.8 else "normal"
        self.notifications.push(
            "cosmos_reasoning",
            f"[Cosmos] {result.action}: {result.reasoning[:100]}",
            priority
        )

        return result

    def _encode_image(self, image_path: str) -> Optional[str]:
        """Encode and resize image to base64 for API.

        Resizes to max_image_dim to fit within ctx_size constraints.
        Tapo cameras capture at 2880x1620 which exceeds 4096 ctx_size.
        """
        try:
            import io
            from PIL import Image
            img = Image.open(image_path)
            img.thumbnail((self.config.max_image_dim, self.config.max_image_dim))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except ImportError:
            # Fallback: send raw if PIL not available
            try:
                with open(image_path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                return None
        except Exception:
            return None

    def _call_cosmos(self, messages: List[Dict]) -> Dict[str, Any]:
        """Call local Cosmos Reason2 via OpenAI-compatible API."""
        if self.config.mock_mode:
            return self._mock_cosmos_response(messages)

        return self._real_cosmos_call(messages)

    def _real_cosmos_call(self, messages: List[Dict]) -> Dict[str, Any]:
        """Make a real call to local llama-server."""
        try:
            import urllib.request

            url = f"{self.server_url}/v1/chat/completions"
            payload = {
                "model": "cosmos-reason2",
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "stream": False,
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                text = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

                # Try to parse structured response
                clean = text.strip()
                if clean.startswith("```"):
                    lines = clean.split("\n")
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    clean = "\n".join(lines)

                try:
                    return json.loads(clean)
                except json.JSONDecodeError:
                    return {
                        "reasoning": text,
                        "action": "observe",
                        "confidence": 0.5,
                        "scene_description": text[:200],
                    }

        except Exception as e:
            self.notifications.push("error", f"Cosmos server error: {e}", "urgent")
            return {
                "reasoning": f"Server error: {e}",
                "action": "fallback",
                "confidence": 0.0,
                "scene_description": "",
            }

    def _mock_cosmos_response(self, messages: List[Dict]) -> Dict[str, Any]:
        """Generate mock egocentric response for testing."""
        prompt_text = str(messages[-1].get("content", ""))
        has_image = "image_url" in prompt_text or any(
            isinstance(m.get("content"), list) and
            any(c.get("type") == "image_url" for c in m["content"] if isinstance(c, dict))
            for m in messages
        )

        if "interact" in prompt_text.lower() or "looking at me" in prompt_text.lower():
            return {
                "reasoning": (
                    "I can see a person in front of me. They are facing my direction "
                    "and appear to be making eye contact. Their body language suggests "
                    "they want to engage with me."
                ),
                "action": "engage",
                "confidence": 0.88,
                "scene_description": "One person facing me, approximately 1.5m away",
            }
        elif "approaching" in prompt_text.lower() or "motion" in prompt_text.lower():
            return {
                "reasoning": (
                    "I detect movement in my field of view. Someone is walking "
                    "toward me from the left side. Based on their trajectory, "
                    "they will reach my position in about 3 seconds."
                ),
                "action": "prepare_greeting",
                "confidence": 0.75,
                "scene_description": "Person approaching from left, 3m distance",
            }
        elif has_image:
            return {
                "reasoning": (
                    "Analyzing the scene from my perspective. I can see the room "
                    "with objects at various distances. No immediate interaction "
                    "needed but I should remain attentive."
                ),
                "action": "observe",
                "confidence": 0.6,
                "scene_description": "Indoor scene, no persons detected in immediate vicinity",
            }
        else:
            return {
                "reasoning": (
                    "Routine observation from my viewpoint. The environment "
                    "appears stable with no new stimuli requiring my attention."
                ),
                "action": "continue_monitoring",
                "confidence": 0.5,
                "scene_description": "Stable environment, no changes detected",
            }

    def _summarize_events(self, events: List[Event]) -> str:
        """Summarize events in first-person perspective."""
        lines = []
        for e in events:
            # Reframe events egocentrically
            if "motion" in e.type.lower():
                lines.append(f"- I detected movement: {e.content}")
            elif "audio" in e.type.lower() or "speech" in e.type.lower():
                lines.append(f"- I heard something: {e.content}")
            else:
                lines.append(f"- My {e.source} sensor reports: {e.content}")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        total = len(self._perceived_events) + self._events_filtered
        return {
            "api_calls": self._api_calls,
            "events_perceived": len(self._perceived_events),
            "events_filtered": self._events_filtered,
            "filter_rate": (
                f"{self._events_filtered / total * 100:.1f}%"
                if total > 0 else "N/A"
            ),
            "reasoning_history": len(self._reasoning_history),
            "mock_mode": self.config.mock_mode,
            "model": self.config.model_name,
            "server_url": self.server_url,
            "circadian_mode": self.circadian.current_mode.value,
        }
