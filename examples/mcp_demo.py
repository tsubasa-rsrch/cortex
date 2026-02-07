#!/usr/bin/env python3
"""Quick demo of Cortex MCP server capabilities.

Shows how to interact with the MCP server programmatically,
demonstrating all 11 perception tools.

Run:  python examples/mcp_demo.py
"""

import json
import subprocess
import sys


def call_mcp(method: str, params: dict = None, tool_name: str = None, tool_args: dict = None) -> dict:
    """Send a JSON-RPC request to the MCP server."""
    if tool_name:
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": tool_args or {}},
        }
    else:
        msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }
    return msg


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    # Build the full MCP handshake + tool calls
    messages = [
        # 1. Initialize
        call_mcp("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "cortex-demo", "version": "0.1"},
        }),
        # 2. Initialized notification
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        # 3. List tools
        call_mcp("tools/list"),
        # 4. Get perception summary
        call_mcp("tools/call", tool_name="cortex_perception_summary", tool_args={}),
        # 5. Check habituation
        call_mcp("tools/call", tool_name="cortex_check_habituation", tool_args={
            "source": "camera_lobby", "value": 25.0,
        }),
        # 6. Check habituation again (should be filtered by cooldown)
        call_mcp("tools/call", tool_name="cortex_check_habituation", tool_args={
            "source": "camera_lobby", "value": 18.0,
        }),
        # 7. Get circadian status
        call_mcp("tools/call", tool_name="cortex_circadian_status", tool_args={}),
        # 8. Push a notification
        call_mcp("tools/call", tool_name="cortex_push_notification", tool_args={
            "ntype": "alert", "message": "Motion detected in lobby", "priority": "urgent",
        }),
        # 9. Decide on events
        call_mcp("tools/call", tool_name="cortex_decide", tool_args={
            "events_json": json.dumps([
                {"source": "camera", "type": "motion", "content": "Person in lobby", "priority": 8},
                {"source": "api", "type": "health", "content": "CPU at 45%", "priority": 2},
            ]),
        }),
        # 10. Start a task
        call_mcp("tools/call", tool_name="cortex_start_task", tool_args={
            "task_name": "Investigate lobby motion",
        }),
        # 11. Add checkpoint
        call_mcp("tools/call", tool_name="cortex_checkpoint", tool_args={
            "note": "Camera feed reviewed",
        }),
    ]

    # Send all messages to MCP server via stdin
    stdin_data = "\n".join(json.dumps(m) for m in messages) + "\n"

    result = subprocess.run(
        [sys.executable, "-m", "cortex.mcp_server"],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=10,
    )

    responses = result.stdout.strip().split("\n")

    print("Cortex MCP Server Demo")
    print("=" * 60)

    labels = [
        "Initialize",
        "List Tools",
        "Perception Summary",
        "Habituation Check #1 (novel stimulus)",
        "Habituation Check #2 (cooldown filter)",
        "Circadian Status",
        "Push Notification",
        "Decision Engine",
        "Start Task",
        "Checkpoint",
    ]

    for i, (label, raw) in enumerate(zip(labels, responses)):
        try:
            data = json.loads(raw)
            result_data = data.get("result", {})

            separator(f"Step {i+1}: {label}")

            if "tools" in result_data:
                tools = result_data["tools"]
                print(f"  {len(tools)} tools available:")
                for t in tools:
                    print(f"    - {t['name']}")
            elif "content" in result_data:
                content = json.loads(result_data["content"][0]["text"])
                print(f"  {json.dumps(content, indent=4)}")
            elif "serverInfo" in result_data:
                info = result_data["serverInfo"]
                print(f"  Server: {info['name']} v{info['version']}")
                print(f"  Protocol: {result_data['protocolVersion']}")
            else:
                print(f"  {json.dumps(result_data, indent=4)}")
        except (json.JSONDecodeError, IndexError, KeyError):
            pass

    print(f"\n{'='*60}")
    print("  Demo complete! All 11 Cortex MCP tools demonstrated.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
