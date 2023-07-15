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

    # debug flags
    default_image_fallback_instant = True
    default_image_fallback_calendar = True
    default_image_fallback_reset = False


def report() -> None:
    """Print the value of a constant by name."""
    print(str(getattr(Constant, sys.argv[1].replace("-", "_"))))


def systemd_services() -> tuple[str, ...]:
    """Report all systemd services."""
    return (Constant.controller_service, Constant.viewer_service, Constant.watcher_service)


# NOTE: This is here to satisfy dead code checks that can't understand bash/cli
# usage of python constructs
def report_bash_settings() -> None:
    """Report settings known to be used only by the bash code and not the python code."""
    print(Constant.default_image_fallback_calendar)


__all__ = ["report", "report_bash_settings", "systemd_services"]
