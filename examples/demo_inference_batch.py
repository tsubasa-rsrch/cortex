#!/usr/bin/env python3
"""Batch inference demo for Cosmos Cookoff video.

Runs egocentric reasoning on multiple images and saves formatted output
suitable for screen recording / demo video.
"""

import json
import io
import time
import base64
import urllib.request
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
except ImportError:
    print("Pillow not installed: pip install Pillow")
    raise

SERVER_URL = "http://127.0.0.1:8090"
MAX_IMAGE_DIM = 384  # Resize to fit 4096 ctx

SYSTEM_PROMPT = (
    "You are a robot with a camera. The camera view IS your view. "
    "Everything you see is from your first-person perspective. "
    "Describe what YOU see, not what 'the camera' sees. "
    "Reason about: who is near you, what they're doing, "
    "whether they want to interact with you."
)

# Demo images with scenario descriptions
DEMO_IMAGES = [
    {
        "path": "/Volumes/T7 Shield/TsubasaImages/tapo_captures/c230_1902.jpg",
        "scenario": "Evening bedroom scene",
        "question": "Looking at what's in front of me right now, what do I see? Is anyone here? What are they doing?",
        "time_label": "21:02 EST",
    },
    {
        "path": "/Volumes/T7 Shield/TsubasaImages/tapo_captures/c260_1902.jpg",
        "scenario": "Evening kitchen scene",
        "question": "From my perspective in the kitchen, who is here and what is happening?",
        "time_label": "21:02 EST",
    },
    {
        "path": "/Volumes/T7 Shield/TsubasaImages/tapo_captures/c230_20260206_130723.jpg",
        "scenario": "Afternoon bedroom scene",
        "question": "I just detected motion. Looking at my view, is someone here? Should I engage or continue observing?",
        "time_label": "13:07 EST",
    },
    {
        "path": "/Volumes/T7 Shield/TsubasaImages/tapo_captures/c260_20260206_130748.jpg",
        "scenario": "Afternoon kitchen scene",
        "question": "My kitchen camera detected activity. What do I see from this angle? Any social interaction happening?",
        "time_label": "13:07 EST",
    },
]

COLORS = {
    "header": "\033[1;36m",  # cyan bold
    "scene": "\033[1;33m",   # yellow bold
    "question": "\033[0;37m", # white
    "response": "\033[1;32m", # green bold
    "stats": "\033[0;35m",   # magenta
    "divider": "\033[0;90m", # dark gray
    "reset": "\033[0m",
}


def encode_image(path: str) -> str:
    """Resize and encode image to base64."""
    img = Image.open(path)
    img.thumbnail((MAX_IMAGE_DIM, MAX_IMAGE_DIM))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def call_vlm(question: str, image_path: str) -> tuple:
    """Call local VLM server and return (response_text, latency_ms)."""
    img_data = encode_image(image_path)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_data}"},
                },
                {"type": "text", "text": question},
            ],
        },
    ]

    payload = {
        "model": "qwen3-vl-2b",
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.3,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{SERVER_URL}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.time()
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    latency = (time.time() - start) * 1000

    text = result["choices"][0]["message"]["content"]
    return text, latency


def print_banner():
    """Print demo banner."""
    c = COLORS
    print(f"\n{c['header']}{'='*70}")
    print(f"  Cortex + Cosmos Reason2: Egocentric Social Reasoning Demo")
    print(f"  Team 668 | tsubasa-rsrch/cortex | NVIDIA Cosmos Cookoff 2026")
    print(f"{'='*70}{c['reset']}\n")
    print(f"{c['stats']}  Model: Qwen3-VL-2B Q4_K_M (1.0GB)")
    print(f"  Hardware: Apple M2, 8GB RAM")
    print(f"  Server: llama.cpp (local, no cloud API)")
    print(f"  Framework: Cortex v0.4.0 (201 tests, 7,169 LOC){c['reset']}\n")


def run_demo():
    """Run the demo batch inference."""
    print_banner()

    c = COLORS
    total_latency = 0
    results = []

    for i, demo in enumerate(DEMO_IMAGES, 1):
        path = demo["path"]
        if not Path(path).exists():
            print(f"{c['divider']}  [SKIP] {path} not found{c['reset']}")
            continue

        print(f"{c['divider']}{'─'*70}{c['reset']}")
        print(f"{c['scene']}  Scene {i}: {demo['scenario']} [{demo['time_label']}]{c['reset']}")
        print(f"{c['question']}  Q: {demo['question']}{c['reset']}")
        print(f"{c['stats']}  Reasoning...{c['reset']}", end="", flush=True)

        text, latency = call_vlm(demo["question"], path)
        total_latency += latency

        print(f"\r{c['stats']}  Inference: {latency:.0f}ms{c['reset']}                    ")
        print(f"{c['response']}  A: {text}{c['reset']}")
        print()

        results.append({
            "scenario": demo["scenario"],
            "time": demo["time_label"],
            "image": Path(path).name,
            "question": demo["question"],
            "response": text,
            "latency_ms": round(latency),
        })

    # Summary
    n = len(results)
    if n > 0:
        avg = total_latency / n
        print(f"{c['divider']}{'─'*70}{c['reset']}")
        print(f"{c['header']}  Summary:{c['reset']}")
        print(f"{c['stats']}  Scenes processed: {n}")
        print(f"  Average latency: {avg:.0f}ms")
        print(f"  Total time: {total_latency:.0f}ms")
        print(f"  All responses in first-person egocentric perspective{c['reset']}")
        print(f"\n{c['header']}  \"The camera view IS my view.\"{c['reset']}\n")

    # Save results
    output = "/Users/tsubasa/Documents/TsubasaWorkspace/cortex/examples/demo_results.json"
    with open(output, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "model": "qwen3-vl-2b-q4_k_m",
            "hardware": "Apple M2, 8GB",
            "results": results,
        }, f, indent=2)
    print(f"{c['stats']}  Results saved to {output}{c['reset']}")


if __name__ == "__main__":
    run_demo()
