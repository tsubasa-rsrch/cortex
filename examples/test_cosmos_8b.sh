#!/bin/bash
# Test Cosmos Reason2-8B local inference on M4 Max 48GB
# Run this after downloading the model and starting llama-server

MODEL_DIR="$HOME/Documents/TsubasaWorkspace/models/cosmos-reason2-8b"
MODEL="$MODEL_DIR/Cosmos-Reason2-8B.Q8_0.gguf"
MMPROJ="$MODEL_DIR/Cosmos-Reason2-8B.mmproj-bf16.gguf"
PORT=8090

echo "=== Cosmos Reason2-8B Local Test ==="
echo "Model: $MODEL"
echo "mmproj: $MMPROJ"
echo ""

# Check files exist
if [ ! -f "$MODEL" ]; then
    echo "ERROR: Model not found at $MODEL"
    echo "Download: curl -L -o $MODEL https://huggingface.co/prithivMLmods/Cosmos-Reason2-8B-GGUF/resolve/main/Cosmos-Reason2-8B.Q8_0.gguf"
    exit 1
fi
if [ ! -f "$MMPROJ" ]; then
    echo "ERROR: mmproj not found at $MMPROJ"
    exit 1
fi

echo "Model size: $(ls -lh "$MODEL" | awk '{print $5}')"
echo "mmproj size: $(ls -lh "$MMPROJ" | awk '{print $5}')"
echo ""

# Check if llama-server is running
if curl -s http://127.0.0.1:$PORT/health > /dev/null 2>&1; then
    echo "llama-server already running on :$PORT"
else
    echo "Starting llama-server on :$PORT..."
    llama-server \
        -m "$MODEL" \
        --mmproj "$MMPROJ" \
        --host 127.0.0.1 --port $PORT \
        -ngl -1 -c 4096 &
    SERVER_PID=$!
    echo "Server PID: $SERVER_PID"
    echo "Waiting for server to start..."
    sleep 10

    if ! curl -s http://127.0.0.1:$PORT/health > /dev/null 2>&1; then
        echo "ERROR: Server failed to start"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    echo "Server ready!"
fi

echo ""
echo "Running egocentric pipeline demo with Cosmos 8B..."
cd "$(dirname "$0")/.."
python3 examples/egocentric_reachy_pipeline.py --demo --real-vlm --cosmos-8b --port $PORT

echo ""
echo "=== Test complete ==="
