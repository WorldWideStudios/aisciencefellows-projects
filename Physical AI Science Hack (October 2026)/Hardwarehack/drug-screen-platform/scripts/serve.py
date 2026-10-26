"""
Start the web API on 127.0.0.1:8000 (loopback only, never the LAN).

    uv run python scripts/serve.py            # add --reload while developing
"""

import sys

import uvicorn

if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
    uvicorn.run("api.app:app", host="127.0.0.1", port=port, reload="--reload" in sys.argv)
