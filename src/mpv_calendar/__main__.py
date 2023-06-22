"""Serve the app."""

import sys
from pathlib import Path

import uvicorn

from .constants import Constant
from .server import app

IP_ADDRESS = "0.0.0.0"  # nosec
LOG_LEVEL = "debug"


HERE = Path(__file__).parent.resolve()


def is_running_from_venv() -> bool:
    """Check if the script is running from a virtual environment."""
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )


def main() -> None:
    """Start the server."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else Constant.port

    uvicorn.run(
        app,
        host=IP_ADDRESS,
        port=port,
        log_level=LOG_LEVEL,
        app_dir=str(HERE),
    )


if __name__ == "__main__":
    main()
