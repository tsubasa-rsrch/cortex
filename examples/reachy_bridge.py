#!/usr/bin/env python3
"""Cortex-ReachyMini Bridge: Connect perception to a physical body.

This bridge maps Cortex's cognitive modules to ReachyMini's physical actions:
  - HabituationFilter → look_at_world() (attend to novel stimuli)
  - CircadianRhythm   → antenna expression (energy/mood display)
  - DecisionEngine     → action routing (decide what to do)
  - NotificationQueue  → orienting response (urgent head turn)

Usage:
    # With real ReachyMini (requires reachy-mini-daemon running):
    python reachy_bridge.py

    # With mockup-sim:
    reachy-mini-daemon --mockup-sim --deactivate-audio --localhost-only
    python reachy_bridge.py
"""

import time
import math
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple, List

from cortex import (
    CortexConfig, set_config,
    HabituationFilter, CircadianRhythm, CircadianMode,
    DecisionEngine, Action, NotificationQueue, Event,
    TimestampLog,
)

# Optional: ReachyMini-specific sources (require numpy)
try:
    from cortex.sources.reachy import (
        ReachyCameraSource, ReachyAudioSource, ReachyIMUSource,
    )
    HAS_REACHY_SOURCES = True
except ImportError:
    HAS_REACHY_SOURCES = False


# --- Antenna Emotion Map ---
# Maps emotional/cognitive states to antenna positions [left, right]
# Range: roughly -20 to 20 degrees (reachy_mini joint limits)

@dataclass
class AntennaExpression:
    """An antenna pose expressing an emotional/cognitive state."""
    name: str
    left: float
    right: float
    duration: float = 0.3  # transition time

EXPRESSIONS = {
    "neutral":  AntennaExpression("neutral",   0.0,   0.0),
    "happy":    AntennaExpression("happy",    15.0,  15.0),
    "excited":  AntennaExpression("excited",  20.0,  20.0),
    "curious":  AntennaExpression("curious",  15.0,  -5.0),
    "thinking": AntennaExpression("thinking", -8.0,  -8.0),
    "alert":    AntennaExpression("alert",    18.0,  18.0),
    "sleepy":   AntennaExpression("sleepy",   -3.0,  -3.0),
    "sad":      AntennaExpression("sad",     -12.0, -12.0),
}


# --- Circadian → Expression Mapping ---
CIRCADIAN_EXPRESSIONS = {
    CircadianMode.MORNING:   "happy",
    CircadianMode.AFTERNOON: "neutral",
    CircadianMode.EVENING:   "thinking",
    CircadianMode.NIGHT:     "sleepy",
}


# --- Look-at targets (world coordinates) ---
# ReachyMini looks at (x, y, z) in meters from its base
LOOK_TARGETS = {
    "forward":  (0.5,  0.0,  0.0),
    "left":     (0.3,  0.3,  0.0),
    "right":    (0.3, -0.3,  0.0),
    "up":       (0.5,  0.0,  0.2),
    "down":     (0.5,  0.0, -0.15),
}


class ReachyCortexBridge:
    """Bridges Cortex perception modules to ReachyMini body actions.

    This is the core integration layer: Cortex (brain) decides,
    ReachyMini (body) moves.
    """

    def __init__(self, host: str = "localhost"):
        # Cortex modules
        set_config(CortexConfig(
            data_dir=Path.home() / ".cortex" / "reachy",
            name="reachy-tsubasa"
        ))
        self.hab = HabituationFilter(
            cooldown=5.0,       # shorter for demo responsiveness
            base_threshold=10.0,
            orienting_mult=3.0,
        )
        self.circadian = CircadianRhythm()
        self.notifications = NotificationQueue()
        self.log = TimestampLog()
        self.decision = DecisionEngine(
            event_handlers={
                "motion": self._handle_motion_event,
                "voice":  self._handle_voice_event,
                "audio":  self._handle_audio_event,
                "imu":    self._handle_imu_event,
            }
        )

        # ReachyMini connection
        self.host = host
        self.mini = None
        self._current_expression = "neutral"

        # Sensor sources (initialized after connection)
        self.sources = []

    def connect(self):
        """Connect to ReachyMini daemon."""
        try:
            from reachy_mini import ReachyMini
            print(f"Connecting to ReachyMini at {self.host}...")
            self.mini = ReachyMini(
                connection_mode="localhost_only",
                timeout=10.0,
                media_backend="no_media",
            )
            self.mini.wake_up()
            time.sleep(0.5)
            print("Connected and awake!")
            return True
        except ImportError:
            print("ERROR: reachy_mini SDK not installed.")
            print("  pip install reachy-mini")
            return False
        except Exception as e:
            print(f"ERROR: Could not connect to ReachyMini: {e}")
            print("  Is reachy-mini-daemon running?")
            print("  reachy-mini-daemon --mockup-sim --deactivate-audio --localhost-only")
            return False

    def _init_sources(self):
        """Initialize sensor sources after connection."""
        if not self.mini or not HAS_REACHY_SOURCES:
            return
        try:
            self.sources.append(ReachyCameraSource(self.mini))
        except Exception:
            pass
        try:
            self.sources.append(ReachyAudioSource(self.mini))
        except Exception:
            pass
        try:
            self.sources.append(ReachyIMUSource(self.mini))
        except Exception:
            pass
        if self.sources:
            names = [s.name for s in self.sources]
            print(f"Sensor sources active: {', '.join(names)}")

    def poll_sources(self) -> List[Event]:
        """Poll all sensor sources and collect events."""
        events = []
        for source in self.sources:
            try:
                events.extend(source.check())
            except Exception:
                pass
        return events

    def disconnect(self):
        """Gracefully shut down."""
        if self.mini:
            try:
                self.set_expression("sleepy")
                time.sleep(0.5)
                self.mini.goto_sleep()
                print("ReachyMini going to sleep. Goodbye!")
            except Exception:
                pass

    # --- Body Actions ---

    def look_at(self, target: str, duration: float = 0.5):
        """Look at a named target direction."""
        if not self.mini:
            return
        coords = LOOK_TARGETS.get(target, LOOK_TARGETS["forward"])
        try:
            self.mini.look_at_world(*coords, duration=duration)
        except Exception as e:
            print(f"  [look_at error: {e}]")

    def set_expression(self, name: str):
        """Set antenna expression by name."""
        if not self.mini:
            return
        expr = EXPRESSIONS.get(name, EXPRESSIONS["neutral"])
        try:
            self.mini.set_target_antenna_joint_positions([expr.left, expr.right])
            self._current_expression = name
        except Exception as e:
            print(f"  [expression error: {e}]")

    def flutter_antennas(self, cycles: int = 3, speed: float = 0.15):
        """Flutter antennas (happy/excited gesture)."""
        if not self.mini:
            return
        for _ in range(cycles):
            self.mini.set_target_antenna_joint_positions([20.0, 20.0])
            time.sleep(speed)
            self.mini.set_target_antenna_joint_positions([5.0, 5.0])
            time.sleep(speed)

    def orienting_response(self, direction: str = "left"):
        """Quick head turn + alert antenna = "what was that?" """
        if not self.mini:
            return
        self.set_expression("alert")
        self.look_at(direction, duration=0.3)
        time.sleep(0.5)
        # Return to forward
        self.look_at("forward", duration=0.5)
        self.set_expression(self._current_expression)

    # --- Event Handlers (for DecisionEngine) ---

    def _handle_motion_event(self, event: Event) -> Action:
        """Handle motion detection events."""
        value = event.raw_data.get("diff_score", 0)
        source = event.source

        should_alert, reason = self.hab.should_notify(source, value)
        if should_alert:
            if "Orienting" in reason:
                return Action("orienting_response", reason,
                              handler=lambda: self.orienting_response("left"))
            else:
                return Action("attend", reason,
                              handler=lambda: self.look_at("left"))
        return Action("ignore", reason)

    def _handle_voice_event(self, event: Event) -> Action:
        """Handle voice/speech events."""
        direction = event.raw_data.get("direction", "front")
        look_target = {"front": "forward", "left": "left",
                       "right": "right", "back": "forward"}.get(direction, "forward")
        return Action("listen", f"Heard: {event.content[:50]}",
                      handler=lambda: (
                          self.set_expression("curious"),
                          self.look_at(look_target, duration=0.4),
                      ))

    def _handle_audio_event(self, event: Event) -> Action:
        """Handle general sound events."""
        rms = event.raw_data.get("rms_energy", 0)
        if rms > 0.05:
            return Action("alert_sound", f"Loud sound (rms={rms:.3f})",
                          handler=lambda: self.set_expression("alert"))
        return Action("ignore", "Background noise")

    def _handle_imu_event(self, event: Event) -> Action:
        """Handle IMU bump/movement events."""
        delta = event.raw_data.get("delta", 0)
        return Action("startle", f"Bumped! (delta={delta:.1f}g)",
                      handler=lambda: (
                          self.set_expression("alert"),
                          self.flutter_antennas(cycles=2, speed=0.1),
                      ))

    # --- Main Loop ---

    def update_circadian_expression(self):
        """Update antenna expression based on current circadian mode."""
        status = self.circadian.check_and_update()
        mode = status["mode"]  # CircadianMode enum
        expr_name = CIRCADIAN_EXPRESSIONS.get(mode, "neutral")
        self.set_expression(expr_name)
        return status

    def process_events(self, events: list):
        """Run events through Cortex decision engine and execute on body."""
        action = self.decision.decide(events)

        if action.handler:
            result = action.execute()
            print(f"  Action: {action.name} -> {result.get('status', '?')}")
        else:
            print(f"  Action: {action.name} (no handler)")

        return action

    def run_demo(self):
        """Run a demonstration of all bridge features."""
        if not self.connect():
            return

        self.log.start_task("demo")
        print("\n=== Cortex-ReachyMini Bridge Demo ===\n")

        try:
            # 1. Circadian Expression
            print("[1] Circadian Rhythm → Antenna Expression")
            status = self.update_circadian_expression()
            mode = status["mode"]
            mode_name = mode.value if isinstance(mode, CircadianMode) else str(mode)
            expr = CIRCADIAN_EXPRESSIONS.get(mode, "neutral")
            print(f"    Mode: {mode_name} → Expression: {expr}")
            time.sleep(1)

            # 2. Emotion Expressions
            print("\n[2] Emotion Expressions")
            for name in ["happy", "curious", "thinking", "alert", "neutral"]:
                print(f"    {name}...")
                self.set_expression(name)
                time.sleep(0.8)

            # 3. Flutter (excited)
            print("\n[3] Flutter Antennas (excited!)")
            self.flutter_antennas(cycles=3)
            time.sleep(0.5)

            # 4. Look Around
            print("\n[4] Looking Around")
            for direction in ["left", "right", "up", "forward"]:
                print(f"    Looking {direction}...")
                self.look_at(direction, duration=0.4)
                time.sleep(0.6)

            # 5. Simulated Motion Events
            print("\n[5] Motion Detection → Habituation")
            for i, diff_val in enumerate([12.0, 18.0, 16.0, 35.0, 10.0]):
                event = Event(
                    source="motion",
                    type="motion",
                    content=f"Motion detected (diff={diff_val})",
                    priority=7 if diff_val > 25 else 4,
                    raw_data={"diff_score": diff_val},
                )
                print(f"    Event {i+1}: diff={diff_val}")
                self.process_events([event])
                time.sleep(0.8)

            # 6. Orienting Response
            print("\n[6] Orienting Response (sudden stimulus)")
            print("    Something unexpected!")
            self.orienting_response("left")
            time.sleep(1)

            # 7. Notification
            print("\n[7] Notification Queue")
            self.notifications.push("alert", "Demo complete!", priority="high")
            formatted = self.notifications.format()
            if formatted:
                for line in formatted.strip().split("\n"):
                    print(f"    {line}")

            # Done
            print("\n[8] Going to sleep...")
            self.set_expression("sleepy")
            time.sleep(1)

        except KeyboardInterrupt:
            print("\n\nInterrupted!")
        finally:
            result = self.log.end_task("demo") or {}
            elapsed_min = result.get("elapsed_min", 0)
            print(f"\nDemo completed ({elapsed_min} min)")
            self.disconnect()


    def run_live(self, poll_interval: float = 0.5, circadian_interval: float = 300.0):
        """Run live mode: continuous perception-action loop.

        Polls sensor sources, processes events through Cortex,
        and executes actions on the body in real time.

        Args:
            poll_interval: Seconds between sensor polls.
            circadian_interval: Seconds between circadian updates.
        """
        if not self.connect():
            return

        self._init_sources()
        self.log.start_task("live")

        # Initial circadian expression
        status = self.update_circadian_expression()
        mode = status["mode"]
        mode_name = mode.value if isinstance(mode, CircadianMode) else str(mode)
        print(f"\n=== Cortex-ReachyMini Live Mode ===")
        print(f"Circadian: {mode_name}")
        print(f"Polling every {poll_interval}s | Ctrl+C to stop\n")

        last_circadian = time.time()
        event_count = 0
        action_count = 0

        try:
            while True:
                # Poll all sensor sources
                events = self.poll_sources()

                if events:
                    event_count += len(events)
                    action = self.process_events(events)
                    if action.handler:
                        action_count += 1

                # Periodic circadian update
                now = time.time()
                if now - last_circadian > circadian_interval:
                    self.update_circadian_expression()
                    last_circadian = now

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\n\nStopping live mode...")
        finally:
            result = self.log.end_task("live") or {}
            elapsed = result.get("elapsed_min", 0)
            print(f"\nLive session: {elapsed} min, {event_count} events, {action_count} actions")
            self.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Cortex-ReachyMini Bridge")
    parser.add_argument("--live", action="store_true",
                        help="Run in live mode (continuous perception-action loop)")
    parser.add_argument("--interval", type=float, default=0.5,
                        help="Sensor polling interval in seconds (default: 0.5)")
    args = parser.parse_args()

    bridge = ReachyCortexBridge(host="localhost")

    if args.live:
        bridge.run_live(poll_interval=args.interval)
    else:
        bridge.run_demo()


if __name__ == "__main__":
    main()
