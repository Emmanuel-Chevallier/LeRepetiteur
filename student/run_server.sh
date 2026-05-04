#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
# Check if GEMINI_API_KEY is set, if not try to read from Gemini_key file
if [ -z "$GEMINI_API_KEY" ] && [ -f "Gemini_key" ]; then
    export GEMINI_API_KEY=$(cat Gemini_key)
fi

python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
