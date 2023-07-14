"""Global constants."""

import os
import sys
from pathlib import Path

CACHE = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")).resolve()


class Constant:
    """Global constants."""

    controller_service = "mpv-calendar-controller"
    viewer_service = "mpv-calendar-viewer"
    watcher_service = "mpv-calendar-watcher"
    live_stream_service = "nginx"

    viewer_kill_filter = f"grep -v {watcher_service} | grep -v {controller_service} | grep -w mpv"
    watcher_kill_filter = (
        f"grep -v {controller_service} | grep -v {viewer_service} | grep -w {watcher_service}"
    )

    default_image = Path.home() / "Pictures/default-display.jpg"
    front_end_debug = os.getenv("FRONT_END_DEBUG", "False").lower() in ("true", "1")
    last_playing_file = CACHE / ".mpv_playing"
    mpv_socket = "/tmp/mpvsocket"  # nosec
    port = 8080
    no_default_image_fallback: bool = True


def report() -> None:
    """Print the value of a constant by name."""
    print(str(getattr(Constant, sys.argv[1].replace("-", "_"))))


def systemd_services() -> tuple[str, ...]:
    """Report all systemd services."""
    return (Constant.controller_service, Constant.viewer_service, Constant.watcher_service)


__all__ = ["report", "systemd_services"]
