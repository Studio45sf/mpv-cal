"""Stop and restart endpoints for a linux service."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse

from .constants import Constant

app = FastAPI()

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@app.get("/")
async def index(request: Request) -> _TemplateResponse:
    """Get the template for the top level html entry point."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/favicon.ico")
async def favicon() -> FileResponse:
    """Serve the favicon.ico file."""
    return FileResponse(path=STATIC_DIR / "favicon.ico", media_type="image/x-icon")


def _run(command: str) -> int:
    """Run a command somewhat insecurely."""
    print(f"Running: {command}")
    return os.system(command)  # nosec


def _service(command: str, service: str, user: bool) -> str:
    if user:
        return f"systemctl {command} --user {service.removesuffix('.service')}.service"
    return f"sudo systemctl {command} {service.removesuffix('.service')}.service"


def _stop_and_disable(service: str, user: bool, kill_filter: str) -> int:
    """Stop and disable a service by name."""
    result = 0

    print("Stopping...")

    result += _run(f"! {_service('is-active', service, user)} || {_service('stop', service, True)}")
    result += _run("sleep 1")
    result += _run(
        f"! {_service('is-enabled', service, user)} || {_service('disable', service, True)}"
    )

    if not kill_filter:
        return result

    # make sure the viewer is dead
    _run("ps aux | grep -v grep | " + kill_filter + ' | awk "{print \\$2}" | xargs kill -9 || :')

    return result


def _restart_service(service: str, user: bool, kill_filter: str) -> int:
    """Stop, disable, enable, then start a service."""
    result = 0
    result += _stop_and_disable(service, user, kill_filter)
    result += _run("sleep 1")
    result += _run(_service("enable", service, user))
    result += _run("sleep 1")
    result += _run(_service("start", service, user))
    return result


def _load_file_and_skip(
    item: str, last_playing_file: Path, default_image_fallback: bool, queue: bool
) -> int:
    """Construct and send the "loadfile" command over the socket."""
    if default_image_fallback:
        loadfile_command = (
            f'echo \'{{ "command": ["loadfile", "{item}", "append-play"] }}'
            f'\n{{ "command": ["loadfile", "{Constant.default_image}", "append-play"] }}\' '
            f"| socat - {Constant.mpv_socket}"
        )
    else:
        loadfile_command = (
            f'echo \'{{ "command": ["loadfile", "{item}", "append-play"] }}\' '
            f"| socat - {Constant.mpv_socket}"
        )

    # Construct and send the "playlist-next" command
    playlist_next_command = (
        'echo \'{ "command": ["playlist-next", "force"] }\' ' f"| socat - {Constant.mpv_socket}"
    )

    last_playing_file.parent.mkdir(exist_ok=True, parents=True)
    last_playing_file.write_text(f"{item}|10000000000000")

    result = 0
    result += _run(loadfile_command)
    if result == 0 and not queue:
        result += _run(playlist_next_command)
    return result


def _next_playlist_item() -> int:
    """Next item in playlist."""
    # Construct and send the "playlist-next" command
    playlist_next_command = (
        'echo \'{ "command": ["playlist-next", "force"] }\' ' f"| socat - {Constant.mpv_socket}"
    )
    return _run(playlist_next_command)


def _previous_playlist_item() -> int:
    """Next item in playlist."""
    # Construct and send the "playlist-next" command
    playlist_next_command = (
        'echo \'{ "command": ["playlist-previous", "force"] }\' ' f"| socat - {Constant.mpv_socket}"
    )
    return _run(playlist_next_command)


def _toggle_play_pause() -> int:
    """Next item in playlist."""
    # Construct and send the "playlist-next" command
    playlist_next_command = (
        'echo \'{ "command": ["cycle", "pause"] }\' ' f"| socat - {Constant.mpv_socket}"
    )
    return _run(playlist_next_command)


def _manage_service(command: str, service: str, user: bool, kill_filter: str) -> dict[str, str]:
    if command == "stop":
        command_part = "stopping"
        command_past = "stopped"
    elif command == "restart":
        command_part = "restarting"
        command_past = "restarted"
    elif command == "reset":
        command_part = "resetting"
        command_past = "was reset"
    else:
        raise ValueError(f"Invalid command: {command}")

    print(f"{command_part.title()} service={service}...")
    result = 0
    if Constant.front_end_debug:
        result += _run(f"notify '{command.title()} service={service}...'")
    else:
        if command == "restart":
            result += _restart_service(service, user, kill_filter)
        elif command == "stop":
            result += _stop_and_disable(service, user, kill_filter)
        elif command == "reset":
            result = _load_file_and_skip(
                item=str(Constant.default_image),
                last_playing_file=Constant.last_playing_file,
                default_image_fallback=Constant.default_image_fallback_reset,
                queue=False,
            )
        else:
            raise ValueError(f"Invalid command: {command}")

    target = "Display" if command == "reset" else "Service"

    if result != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not {command.lower()} the {target.lower()}.",
        )

    return {"message": f"{target} {command_past.lower()} successfully."}


@app.get("/stop")
async def stop() -> dict[str, str]:
    """Stop services."""
    _manage_service("stop", Constant.viewer_service, True, Constant.viewer_kill_filter)
    return _manage_service("stop", Constant.watcher_service, True, Constant.watcher_kill_filter)


@app.get("/restart")
async def restart() -> dict[str, str]:
    """Restart services."""
    _manage_service("restart", Constant.viewer_service, True, Constant.viewer_kill_filter)
    return _manage_service("restart", Constant.watcher_service, True, Constant.watcher_kill_filter)


@app.get("/stop-live-stream")
async def stop_live_stream() -> dict[str, str]:
    """Stop live stream server."""
    return _manage_service("stop", Constant.live_stream_service, False, "")


@app.get("/restart-live-stream")
async def restart_live_stream() -> dict[str, str]:
    """Restart live stream server."""
    return _manage_service("restart", Constant.live_stream_service, False, "")


@app.get("/stop-viewer")
async def stop_viewer() -> dict[str, str]:
    """Stop viewer service."""
    return _manage_service("restart", Constant.viewer_service, True, Constant.viewer_kill_filter)


@app.get("/restart-viewer")
async def restart_viewer() -> dict[str, str]:
    """Restart viewer service."""
    return _manage_service("restart", Constant.viewer_service, True, Constant.viewer_kill_filter)


@app.get("/stop-watcher")
async def stop_watcher() -> dict[str, str]:
    """Stop calendar watcher service."""
    return _manage_service("restart", Constant.watcher_service, True, Constant.watcher_kill_filter)


@app.get("/restart-watcher")
async def restart_watcher() -> dict[str, str]:
    """Restart calendar watcher service."""
    return _manage_service("restart", Constant.watcher_service, True, Constant.watcher_kill_filter)


@app.get("/reset")
async def reset() -> dict[str, str]:
    """Reset the image."""
    return _manage_service("reset", "", True, "")


@app.get("/toggle-play")
async def toggle_play() -> dict[str, str]:
    """Toggle mpv play state."""
    result = _toggle_play_pause()
    if result != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not toggle play/pause state.",
        )
    return {"message": "Play/pause toggled successfully."}


@app.get("/next")
async def next_playlist_item() -> dict[str, str]:
    """Go to next video in playlist."""
    result = _next_playlist_item()
    if result != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not go to the next item.",
        )
    return {"message": "Next playlist item."}


@app.get("/previous")
async def previous_playlist_item() -> dict[str, str]:
    """Go to previous video in playlist."""
    result = _previous_playlist_item()
    if result != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not go to the previous item.",
        )
    return {"message": "Previous playlist item."}


@app.post("/add")
async def add_playlist_item(request: Request) -> dict[str, str]:
    """Add an item to the playlist and play it immediately."""
    result = await _add(request, queue=False)
    return result


@app.post("/queue")
async def queue_playlist_item(request: Request) -> dict[str, str]:
    """Queue an item to the playlist."""
    result = await _add(request, queue=False)
    return result


async def _add(request: Request, queue: bool) -> dict[str, str]:
    form_data = await request.form()

    item = cast(str, form_data["item"])
    if "://" not in item and not Path(item).is_file():
        if (Path.home() / item).is_file():
            item = str(Path.home() / item)
    elif item.startswith("/") and not Path(item).is_file():
        if (Path.home() / item.removesuffix("/")).is_file():
            item = str(Path.home() / item.removesuffix("/"))

    result = _load_file_and_skip(
        item=item,
        last_playing_file=Constant.last_playing_file,
        default_image_fallback=Constant.default_image_fallback_instant,
        queue=queue,
    )

    if result != 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add item {item} to the playlist.",
        )
    return {"status": "success", "message": f"Item {item} added successfully"}


__all__ = [
    "add_playlist_item",
    "favicon",
    "index",
    "next_playlist_item",
    "previous_playlist_item",
    "queue_playlist_item",
    "reset",
    "restart",
    "restart_live_stream",
    "restart_viewer",
    "restart_watcher",
    "stop",
    "stop_live_stream",
    "stop_viewer",
    "stop_watcher",
    "toggle_play",
]
