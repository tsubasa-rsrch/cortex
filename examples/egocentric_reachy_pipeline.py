#!/usr/bin/env python3
"""Egocentric Reachy Pipeline: Camera → Cortex → VLM → ReachyMini.

The full perception-reasoning-action loop for the Cosmos Cookoff demo.
Connects the two bridges:
  CortexCosmosBridge (perception + reasoning) → ReachyCortexBridge (physical body)

Maps VLM egocentric reasoning to ReachyMini physical responses:
  "I see a person approaching" → excited expression, look toward them
  "Someone is relaxing, no interaction" → quiet observe mode
  "Sudden movement detected" → orienting response, alert

Usage:
    # Demo mode (pre-recorded images, mock ReachyMini):
    python egocentric_reachy_pipeline.py --demo

    # Live mode (real cameras + real ReachyMini):
    python egocentric_reachy_pipeline.py --live

    # VLM-only mode (no ReachyMini, just reasoning):
    python egocentric_reachy_pipeline.py --vlm-only
"""

import time
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable

from cortex import (
    HabituationFilter, CircadianRhythm, CircadianMode,
    NotificationQueue, Event,
)
from cortex.bridges.cosmos import CortexCosmosBridge, CosmosConfig, EgocentricResult


# --- Action → Body Response Mapping ---

@dataclass
class BodyResponse:
    """Physical response for ReachyMini based on VLM reasoning."""
    expression: str          # antenna expression name
    look_target: str         # where to look ("forward", "left", etc.)
    preset: Optional[str]    # emotion preset from library (e.g. "cheerful1")
    flutter: bool            # whether to flutter antennas
    description: str         # human-readable description

    def __repr__(self):
        parts = [f"expr={self.expression}"]
        if self.preset:
            parts.append(f"preset={self.preset}")
        if self.flutter:
            parts.append("flutter!")
        parts.append(f"look={self.look_target}")
        return f"BodyResponse({', '.join(parts)})"


# Map VLM action keywords → physical responses
# These are matched against EgocentricResult.action and reasoning text
ACTION_RESPONSE_MAP: Dict[str, BodyResponse] = {
    "engage": BodyResponse(
        expression="happy",
        look_target="forward",
        preset="cheerful1",
        flutter=True,
        description="Someone wants to interact! Cheerful greeting.",
    ),
    "prepare_greeting": BodyResponse(
        expression="excited",
        look_target="forward",
        preset="curious1",
        flutter=True,
        description="Person approaching. Preparing to greet.",
    ),
    "observe": BodyResponse(
        expression="curious",
        look_target="forward",
        preset=None,
        flutter=False,
        description="Interesting scene. Observing quietly.",
    ),
    "continue_monitoring": BodyResponse(
        expression="neutral",
        look_target="forward",
        preset=None,
        flutter=False,
        description="Nothing new. Continuing to monitor.",
    ),
    "alert": BodyResponse(
        expression="alert",
        look_target="left",
        preset=None,
        flutter=False,
        description="Something unexpected! Alert mode.",
    ),
    "sleep": BodyResponse(
        expression="sleepy",
        look_target="down",
        preset="sleep1",
        flutter=False,
        description="Quiet environment. Resting.",
    ),
    "fallback": BodyResponse(
        expression="thinking",
        look_target="forward",
        preset="thoughtful1",
        flutter=False,
        description="Uncertain. Thinking about what to do.",
    ),
}

# Map confidence thresholds to response intensity
CONFIDENCE_THRESHOLDS = {
    0.8: "high",    # strong response
    0.6: "medium",  # moderate response
    0.0: "low",     # minimal response
}


def reasoning_to_response(result: EgocentricResult) -> BodyResponse:
    """Map VLM egocentric reasoning to a physical body response.

    Strategy:
    1. Check EgocentricResult.action against known actions
    2. If unknown, analyze reasoning text for keywords
    3. Modulate response based on confidence level
    """
    action = result.action.lower().strip()

    # Direct action match
    if action in ACTION_RESPONSE_MAP:
        return ACTION_RESPONSE_MAP[action]

    # Keyword matching in reasoning text
    reasoning_lower = result.reasoning.lower()

    if any(w in reasoning_lower for w in ["approaching", "walking toward", "coming"]):
        return ACTION_RESPONSE_MAP["prepare_greeting"]
    if any(w in reasoning_lower for w in ["interact", "eye contact", "facing me"]):
        return ACTION_RESPONSE_MAP["engage"]
    if any(w in reasoning_lower for w in ["sudden", "unexpected", "startle"]):
        return ACTION_RESPONSE_MAP["alert"]
    if any(w in reasoning_lower for w in ["quiet", "calm", "sleeping", "relaxing"]):
        resp = ACTION_RESPONSE_MAP["observe"]
        if result.confidence < 0.4:
            resp = ACTION_RESPONSE_MAP["sleep"]
        return resp

    # Default: observe
    return ACTION_RESPONSE_MAP["observe"]


def get_confidence_level(confidence: float) -> str:
    """Get response intensity from confidence score."""
    for threshold, level in sorted(CONFIDENCE_THRESHOLDS.items(), reverse=True):
        if confidence >= threshold:
            return level
    return "low"


# --- Unified Pipeline ---

class EgocentricReachyPipeline:
    """Full pipeline: Camera → Cortex perception → VLM reasoning → ReachyMini body.

    This is the core of the Cosmos Cookoff demo.
    """

    def __init__(
        self,
        cosmos_config: Optional[CosmosConfig] = None,
        use_reachy: bool = True,
    ):
        # Cosmos bridge (perception + VLM reasoning)
        self.cosmos = CortexCosmosBridge(cosmos_config)

        # ReachyMini body (optional)
        self.use_reachy = use_reachy
        self.mini = None
        self._presets = None

        # Stats
        self.total_events = 0
        self.total_reasoned = 0
        self.total_responded = 0

    def connect_reachy(self) -> bool:
        """Connect to ReachyMini and load emotion presets."""
        if not self.use_reachy:
            return False
        try:
            from reachy_mini import ReachyMini
            self.mini = ReachyMini(
                connection_mode="localhost_only",
                timeout=10.0,
                media_backend="no_media",
            )
            self.mini.wake_up()
            time.sleep(0.5)
            self._load_presets()
            print("ReachyMini connected and awake!")
            return True
        except ImportError:
            print("reachy-mini SDK not installed. Running VLM-only mode.")
            self.use_reachy = False
            return False
        except Exception as e:
            print(f"Could not connect to ReachyMini: {e}")
            self.use_reachy = False
            return False

    def _load_presets(self):
        """Load emotion preset library."""
        try:
            from reachy_mini.recording import RecordedMoves
            self._presets = RecordedMoves(
                "pollen-robotics/reachy-mini-emotions-library"
            )
            print(f"Loaded emotion presets ({len(self._presets)} available)")
        except Exception:
            self._presets = None

    def execute_body_response(self, response: BodyResponse, confidence: float):
        """Execute a body response on ReachyMini."""
        if not self.mini:
            return

        intensity = get_confidence_level(confidence)

        # 1. Set antenna expression
        from cortex import CortexConfig  # avoid circular
        expr_map = {
            "happy":    [15.0, 15.0],
            "excited":  [20.0, 20.0],
            "curious":  [15.0, -5.0],
            "thinking": [-8.0, -8.0],
            "alert":    [18.0, 18.0],
            "sleepy":   [-3.0, -3.0],
            "neutral":  [0.0, 0.0],
        }
        antenna_pos = expr_map.get(response.expression, [0.0, 0.0])
        try:
            self.mini.set_target_antenna_joint_positions(antenna_pos)
        except Exception:
            pass

        # 2. Look at target
        look_coords = {
            "forward": (0.5, 0.0, 0.0),
            "left":    (0.3, 0.3, 0.0),
            "right":   (0.3, -0.3, 0.0),
            "up":      (0.5, 0.0, 0.2),
            "down":    (0.5, 0.0, -0.15),
        }
        coords = look_coords.get(response.look_target, (0.5, 0.0, 0.0))
        duration = 0.3 if intensity == "high" else 0.5
        try:
            self.mini.look_at_world(*coords, duration=duration)
        except Exception:
            pass

        # 3. Play emotion preset if available and high confidence
        if response.preset and self._presets and intensity in ("high", "medium"):
            try:
                move = self._presets.get(response.preset)
                if move:
                    self.mini.play_move(move, initial_goto_duration=0.5, sound=False)
            except Exception:
                pass

        # 4. Flutter if flagged
        if response.flutter and intensity == "high":
            try:
                for _ in range(3):
                    self.mini.set_target_antenna_joint_positions([20.0, 20.0])
                    time.sleep(0.15)
                    self.mini.set_target_antenna_joint_positions([5.0, 5.0])
                    time.sleep(0.15)
            except Exception:
                pass

        self.total_responded += 1

    def process_frame(
        self,
        image_path: str,
        events: Optional[List[Event]] = None,
        question: Optional[str] = None,
    ) -> Optional[EgocentricResult]:
        """Process a single camera frame through the full pipeline.

        Steps:
        1. Cortex perception filter (if events provided)
        2. VLM egocentric reasoning
        3. Map reasoning → body response
        4. Execute on ReachyMini

        Returns the EgocentricResult for logging/display.
        """
        # Step 1: Perception filter
        if events:
            self.total_events += len(events)
            novel = self.cosmos.perceive(events)
            if not novel and question is None:
                return None  # All filtered out

        # Step 2: VLM reasoning
        if question is None:
            question = (
                "Looking at my current view, what do I see? "
                "Is anyone here? What are they doing? "
                "Should I engage or continue observing?"
            )

        result = self.cosmos.reason_about_scene(question, image_path)
        self.total_reasoned += 1

        # Step 3: Map to body response
        response = reasoning_to_response(result)

        # Step 4: Execute on ReachyMini
        self.execute_body_response(response, result.confidence)

        return result

    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        cosmos_stats = self.cosmos.get_stats()
        return {
            **cosmos_stats,
            "total_events": self.total_events,
            "total_reasoned": self.total_reasoned,
            "total_responded": self.total_responded,
            "reachy_connected": self.mini is not None,
        }


# --- Demo & Live Modes ---

COLORS = {
    "header": "\033[1;36m",
    "scene":  "\033[1;33m",
    "vlm":    "\033[1;32m",
    "body":   "\033[1;35m",
    "stats":  "\033[0;90m",
    "reset":  "\033[0m",
}


def run_demo(pipeline: EgocentricReachyPipeline):
    """Run demo with pre-recorded images."""
    c = COLORS

    demo_images = [
        {
            "path": "/Volumes/T7 Shield/TsubasaImages/tapo_captures/c230_1902.jpg",
            "scenario": "Evening bedroom - someone at the door",
            "question": "I see movement near the door. Who is there? Should I greet them?",
            "events": [Event("camera", "motion", "Movement near door", 6,
                            raw_data={"diff": 22.0})],
        },
        {
            "path": "/Volumes/T7 Shield/TsubasaImages/tapo_captures/c260_1902.jpg",
            "scenario": "Kitchen - person watching TV with cat",
            "question": "From my kitchen view, who is here and what are they doing?",
            "events": [Event("camera", "motion", "Person on couch", 4,
                            raw_data={"diff": 15.0})],
        },
        {
            "path": "/Volumes/T7 Shield/TsubasaImages/tapo_captures/c260_20260206_130748.jpg",
            "scenario": "Afternoon kitchen - person on device",
            "question": "Someone is in the living room. Are they interested in interacting with me?",
            "events": [Event("camera", "motion", "Person detected", 5,
                            raw_data={"diff": 18.0})],
        },
    ]

    print(f"\n{c['header']}{'='*70}")
    print(f"  Egocentric Reachy Pipeline Demo")
    print(f"  Camera → Cortex → Cosmos VLM → ReachyMini")
    print(f"  Team 668 | NVIDIA Cosmos Cookoff 2026")
    print(f"{'='*70}{c['reset']}\n")

    for i, demo in enumerate(demo_images, 1):
        path = demo["path"]
        if not Path(path).exists():
            print(f"{c['stats']}  [SKIP] {path} not found{c['reset']}")
            continue

        print(f"{c['scene']}  Scene {i}: {demo['scenario']}{c['reset']}")
        print(f"{c['stats']}  Q: {demo['question']}{c['reset']}")
        print(f"{c['stats']}  Processing...{c['reset']}", end="", flush=True)

        result = pipeline.process_frame(
            image_path=path,
            events=demo["events"],
            question=demo["question"],
        )

        if result:
            response = reasoning_to_response(result)
            confidence = get_confidence_level(result.confidence)

            print(f"\r{c['vlm']}  VLM ({result.latency_ms:.0f}ms): "
                  f"{result.reasoning[:120]}{c['reset']}")
            print(f"{c['body']}  Body: {response.description} "
                  f"[{response.expression}, confidence={confidence}]{c['reset']}")
        else:
            print(f"\r{c['stats']}  Filtered by habituation{c['reset']}")

        print()
        time.sleep(0.5)

    # Summary
    stats = pipeline.get_stats()
    print(f"{c['header']}  Pipeline Stats:{c['reset']}")
    print(f"{c['stats']}  Events: {stats['total_events']} | "
          f"Reasoned: {stats['total_reasoned']} | "
          f"Responded: {stats['total_responded']} | "
          f"Filter rate: {stats['filter_rate']}")
    print(f"  Model: {stats['model']} | "
          f"Reachy: {'connected' if stats['reachy_connected'] else 'VLM-only'}")
    print(f"  \"The camera view IS my view.\"{c['reset']}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Egocentric Reachy Pipeline: Camera → Cortex → VLM → ReachyMini"
    )
    parser.add_argument("--demo", action="store_true",
                        help="Run demo with pre-recorded images")
    parser.add_argument("--live", action="store_true",
                        help="Run live mode with real cameras")
    parser.add_argument("--vlm-only", action="store_true",
                        help="VLM reasoning only, no ReachyMini")
    parser.add_argument("--mock", action="store_true", default=True,
                        help="Use mock VLM responses (default: True)")
    parser.add_argument("--real-vlm", action="store_true",
                        help="Use real VLM server (llama-server on :8090)")
    parser.add_argument("--port", type=int, default=8090,
                        help="VLM server port (default: 8090)")
    args = parser.parse_args()

    # Configure
    mock_mode = not args.real_vlm
    use_reachy = not args.vlm_only

    config = CosmosConfig(
        mock_mode=mock_mode,
        server_port=args.port,
        model_name="qwen3-vl-2b" if not mock_mode else "mock",
    )

    pipeline = EgocentricReachyPipeline(
        cosmos_config=config,
        use_reachy=use_reachy,
    )

    # Connect ReachyMini if requested
    if use_reachy:
        pipeline.connect_reachy()

    if args.live:
        print("Live mode not yet implemented (waiting for cameras + ReachyMini)")
        print("Use --demo for pre-recorded image demo")
    else:
        run_demo(pipeline)


if __name__ == "__main__":
    main()
