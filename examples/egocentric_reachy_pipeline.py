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

import os
import time
import argparse
import subprocess
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
            self.mini = ReachyMini(media_backend="no_media")
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


# --- Camera Capture ---

CAMERAS = {
    "bedroom": "rtsp://Tsubasa2:IloveKana20241119@10.0.197.118:554/stream1",
    "kitchen": "rtsp://Tsubasa:IloveKana20241119@10.0.55.43:554/stream1",
}

REACHY_CMD_PATH = Path("/tmp/reachy_command")


def capture_frame(camera: str = "bedroom", output: str = "/tmp/cosmos_live_frame.jpg") -> Optional[str]:
    """Capture a single frame from Tapo camera via RTSP."""
    rtsp_url = CAMERAS.get(camera)
    if not rtsp_url:
        print(f"  Unknown camera: {camera}")
        return None
    try:
        subprocess.run(
            ["ffmpeg", "-rtsp_transport", "tcp", "-i", rtsp_url,
             "-frames:v", "1", "-y", "-loglevel", "error", output],
            timeout=10, capture_output=True,
        )
        if Path(output).exists() and Path(output).stat().st_size > 1000:
            return output
    except Exception as e:
        print(f"  Capture failed: {e}")
    return None


def compute_frame_diff(frame_a: str, frame_b: str) -> float:
    """Compute average pixel difference between two frames (0-255 scale)."""
    try:
        from PIL import Image
        import numpy as np
        a = np.array(Image.open(frame_a).resize((160, 90)))
        b = np.array(Image.open(frame_b).resize((160, 90)))
        return float(np.mean(np.abs(a.astype(float) - b.astype(float))))
    except Exception:
        return 15.0  # assume moderate change on error


def send_to_reachy_hub(response: BodyResponse, result: EgocentricResult):
    """Send body response to reachy_hub via /tmp/reachy_command.

    Uses reachy_hub's full feature set: MioTTS, inline motion tags,
    compound commands, speech wobble, etc.
    """
    parts = []

    # Emotion preset
    if response.preset:
        parts.append(response.preset)

    # Speech with inline motion tag
    speech = result.reasoning[:80]
    if response.flutter:
        parts.append(f"say:[flutter]{speech}")
    elif response.preset:
        parts.append(f"say:[{response.preset}]{speech}")
    else:
        parts.append(f"say:{speech}")

    # Combine into compound command
    cmd = ";".join(parts) if len(parts) > 1 else parts[0] if parts else ""
    if cmd:
        try:
            REACHY_CMD_PATH.write_text(cmd)
        except Exception:
            pass


def run_live(
    pipeline: EgocentricReachyPipeline,
    camera: str = "bedroom",
    interval: float = 10.0,
    motion_threshold: float = 8.0,
    use_hub: bool = True,
    force_first: bool = False,
    max_cycles: int = 0,
):
    """Run live pipeline: Camera → Cortex → VLM → ReachyMini.

    Captures frames at regular intervals, detects motion via frame diff,
    feeds novel events through Cortex habituation, and triggers VLM +
    ReachyMini response for significant changes.
    """
    c = COLORS

    print(f"\n{c['header']}{'='*70}")
    print(f"  Egocentric Reachy Pipeline — LIVE MODE")
    print(f"  Camera: {camera} | Interval: {interval}s | Threshold: {motion_threshold}")
    print(f"  Ctrl+C to stop")
    print(f"{'='*70}{c['reset']}\n")

    prev_frame = "/tmp/cosmos_prev_frame.jpg"
    curr_frame = "/tmp/cosmos_curr_frame.jpg"
    cycle = 0

    # Capture initial reference frame
    print(f"{c['stats']}  Capturing reference frame...{c['reset']}")
    ref = capture_frame(camera, prev_frame)
    if not ref:
        print(f"{c['stats']}  Could not capture from {camera}. Check camera connection.{c['reset']}")
        return

    try:
        while True:
            cycle += 1
            if max_cycles and cycle > max_cycles:
                print(f"\n{c['stats']}  Reached max cycles ({max_cycles}). Stopping.{c['reset']}")
                break
            time.sleep(interval)

            # Capture current frame
            frame = capture_frame(camera, curr_frame)
            if not frame:
                continue

            # Compute motion diff
            diff = compute_frame_diff(prev_frame, curr_frame)
            timestamp = time.strftime("%H:%M:%S")

            is_first = (cycle == 1 and force_first)

            if diff < motion_threshold and not is_first:
                # No significant motion — habituated
                print(f"{c['stats']}  [{timestamp}] cycle={cycle} diff={diff:.1f} "
                      f"(below {motion_threshold}) — habituated{c['reset']}")
                # Swap frames for next comparison
                os.replace(curr_frame, prev_frame)
                continue

            # Motion detected (or forced first frame) — run through Cortex + VLM
            label = "FIRST FRAME (forced)" if is_first else "MOTION DETECTED"
            print(f"\n{c['scene']}  [{timestamp}] cycle={cycle} diff={diff:.1f} "
                  f"— {label}{c['reset']}")

            if is_first:
                # Bypass Cortex filter for first frame, go direct to VLM
                result = pipeline.process_frame(
                    image_path=curr_frame,
                    events=None,
                    question=(
                        "This is my first look around. What do I see from my perspective? "
                        "Who is here? What's the environment like?"
                    ),
                )
            else:
                events = [Event("camera", "motion",
                               f"Motion detected (diff={diff:.1f})", 5,
                               raw_data={"diff": diff})]
                result = pipeline.process_frame(
                    image_path=curr_frame,
                    events=events,
                )

            if result:
                response = reasoning_to_response(result)
                confidence = get_confidence_level(result.confidence)

                print(f"{c['vlm']}  VLM ({result.latency_ms:.0f}ms): "
                      f"{result.reasoning[:120]}{c['reset']}")
                print(f"{c['body']}  Body: {response.description} "
                      f"[{response.expression}, conf={confidence}]{c['reset']}")

                # Send to reachy_hub if available
                if use_hub and REACHY_CMD_PATH.parent.exists():
                    send_to_reachy_hub(response, result)
                    print(f"{c['stats']}  → Sent to reachy_hub{c['reset']}")
            else:
                print(f"{c['stats']}  Filtered by Cortex habituation{c['reset']}")

            # Swap frames
            os.replace(curr_frame, prev_frame)

    except KeyboardInterrupt:
        print(f"\n{c['header']}  Stopped. Pipeline stats:{c['reset']}")
        stats = pipeline.get_stats()
        print(f"{c['stats']}  Events: {stats['total_events']} | "
              f"Reasoned: {stats['total_reasoned']} | "
              f"Filter rate: {stats['filter_rate']}{c['reset']}")


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
    parser.add_argument("--cosmos-8b", action="store_true",
                        help="Use Cosmos Reason2-8B (requires M4 Max 48GB)")
    parser.add_argument("--camera", choices=["bedroom", "kitchen"],
                        default="bedroom", help="Camera to use in live mode")
    parser.add_argument("--interval", type=float, default=10.0,
                        help="Capture interval in seconds (live mode)")
    parser.add_argument("--threshold", type=float, default=8.0,
                        help="Motion detection threshold (live mode)")
    parser.add_argument("--no-hub", action="store_true",
                        help="Don't send commands to reachy_hub")
    parser.add_argument("--force-first", action="store_true",
                        help="Force VLM reasoning on first frame (demo/recording)")
    parser.add_argument("--max-cycles", type=int, default=0,
                        help="Max cycles before stopping (0=infinite)")
    args = parser.parse_args()

    # Configure
    mock_mode = not args.real_vlm
    use_reachy = not args.vlm_only and not args.no_hub

    if args.cosmos_8b:
        model_name = "cosmos-reason2-8b"
    elif not mock_mode:
        model_name = "cosmos-reason2"
    else:
        model_name = "mock"

    config = CosmosConfig(
        mock_mode=mock_mode,
        server_port=args.port,
        model_name=model_name,
    )

    pipeline = EgocentricReachyPipeline(
        cosmos_config=config,
        use_reachy=use_reachy,
    )

    # Connect ReachyMini SDK if needed (demo mode)
    if use_reachy and not args.live:
        pipeline.connect_reachy()

    if args.live:
        run_live(
            pipeline,
            camera=args.camera,
            interval=args.interval,
            motion_threshold=args.threshold,
            use_hub=not args.no_hub,
            force_first=args.force_first,
            max_cycles=args.max_cycles,
        )
    else:
        run_demo(pipeline)


if __name__ == "__main__":
    main()
