#!/bin/bash
# Start the Schwab portfolio API on localhost:8765
# Override data dir: SCHWAB_BASE_DIR=/path/to/data ./start_api.sh
cd "$(dirname "$0")"
exec uv run uvicorn api.main:app --host 127.0.0.1 --port 8765 --reload
