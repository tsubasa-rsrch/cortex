#!/usr/bin/env python3
"""Egocentric reasoning demo using Cortex + local VLM.

Captures a frame from Tapo camera, runs it through Cortex perception
filters, then sends to local Qwen3-VL for egocentric scene understanding.

Usage:
    python3 egocentric_demo.py                    # Single frame analysis
    python3 egocentric_demo.py --loop              # Continuous monitoring
    python3 egocentric_demo.py --image /path.jpg   # Analyze existing image
    python3 egocentric_demo.py --mock              # Mock mode (no camera/VLM needed)
"""

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# Cortex imports (if installed)
try:
    from cortex.bridges.cosmos import CortexCosmosBridge, CosmosConfig
    from cortex.sources.base import Event
    HAS_CORTEX = True
except ImportError:
    HAS_CORTEX = False


# --- Configuration ---

CAMERAS = {
    "bedroom": {
        "rtsp": "rtsp://TsubasaCam:CamPassword668@10.0.0.148:554/stream1",
        "name": "C230 Bedroom",
    },
    "kitchen": {
        "rtsp": "rtsp://TsubasaCam:CamPassword668@10.0.0.214:554/stream1",
        "name": "C260 Kitchen",
    },
}

VLM_URL = "http://127.0.0.1:8090/v1/chat/completions"
VLM_MODEL = "qwen3-vl-2b"

EGOCENTRIC_SYSTEM = (
    "You are a robot observing your surroundings. The camera is YOUR eye. "
    "Describe what you see in first person. Focus on: "
    "1) Who is present and what are they doing? "
    "2) Is anyone trying to interact with you? "
    "3) What should you do?"
)


def capture_frame(camera_key="bedroom", output_path="/tmp/ego_frame.jpg"):
    """Capture a single frame from Tapo camera via RTSP."""
    cam = CAMERAS.get(camera_key, CAMERAS["bedroom"])
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-rtsp_transport", "tcp",
                "-i", cam["rtsp"],
                "-frames:v", "1", "-q:v", "2",
                output_path, "-y",
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and Path(output_path).exists():
            return output_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def encode_image(path):
    """Base64 encode an image file."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def vlm_reason(image_path, question="What do I see? Is anyone here?"):
    """Send image + question to local VLM server."""
    img_b64 = encode_image(image_path)

    payload = {
        "model": VLM_MODEL,
        "messages": [
            {"role": "system", "content": EGOCENTRIC_SYSTEM},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    },
                    {"type": "text", "text": question},
                ],
            },
        ],
        "max_tokens": 300,
        "temperature": 0.3,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        VLM_URL, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        latency = time.time() - start

    text = result["choices"][0]["message"]["content"]
    return text, latency


def print_result(camera, text, latency, timestamp=None):
    """Pretty-print reasoning result."""
    ts = timestamp or datetime.now().strftime("%H:%M:%S")
    print(f"\n{'='*60}")
    print(f"  [{ts}] Egocentric Reasoning ({camera})")
    print(f"  Latency: {latency:.1f}s")
    print(f"{'='*60}")
    print(f"\n{text}\n")


def run_single(args):
    """Run single frame analysis."""
    if args.image:
        image_path = args.image
        camera = "file"
    else:
        print(f"Capturing from {args.camera}...")
        image_path = capture_frame(args.camera)
        camera = CAMERAS[args.camera]["name"]
        if not image_path:
            print(f"Failed to capture from {args.camera}. Camera may be offline.")
            return False

    if args.mock:
        print_result(camera, "[MOCK] I see a room. No one is here.", 0.0)
        return True

    print("Sending to VLM for egocentric reasoning...")
    try:
        text, latency = vlm_reason(image_path, args.question)
        print_result(camera, text, latency)
        return True
    except Exception as e:
        print(f"VLM error: {e}")
        print("Is llama-server running on port 8090?")
        return False


def run_loop(args):
    """Continuous monitoring loop."""
    print(f"Starting egocentric monitoring (camera: {args.camera})")
    print(f"Interval: {args.interval}s | Press Ctrl+C to stop\n")

    count = 0
    while True:
        try:
            count += 1
            print(f"--- Frame {count} ---")
            run_single(args)
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print(f"\nStopped after {count} frames.")
            break


def main():
    parser = argparse.ArgumentParser(description="Egocentric reasoning demo")
    parser.add_argument("--camera", default="bedroom", choices=["bedroom", "kitchen"])
    parser.add_argument("--image", help="Analyze existing image instead of capturing")
    parser.add_argument("--question", default="I just detected motion. What do I see? Is anyone here? Should I react?")
    parser.add_argument("--loop", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", type=float, default=10.0, help="Loop interval (seconds)")
    parser.add_argument("--mock", action="store_true", help="Mock mode (no camera/VLM)")

    args = parser.parse_args()

    if args.loop:
        run_loop(args)
    else:
        run_single(args)


if __name__ == "__main__":
    main()
