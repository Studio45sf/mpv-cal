"""Find events from public calendars in a time window."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from itertools import chain

from dateutil import tz
from ics import Calendar
from requests import get

APPLE_PRODID = "PRODID:-//Apple Inc.//Mac OS X 10.15.6//EN\r\n"
CALENDAR_REQUEST_TIMEOUT = 300  # seconds


def _insert_prodid(calendar_content: str, prodid: str) -> str:
    """Insert a dummy prodid if it is missing."""
    # Define PRODID line
    prodid_line = f"PRODID:{prodid}"

    # Split calendar content into lines
    lines = calendar_content.split("\n")

    # Find the index of BEGIN:VCALENDAR
    for i, line in enumerate(lines):
        if line.strip() == "BEGIN:VCALENDAR":
            # Insert the PRODID line after BEGIN:VCALENDAR
            lines.insert(i + 1, prodid_line)
            break

    # Join the lines back into a single string and return
    return "\n".join(lines)


def _calendar_events(
    calendar_url: str,
    start_time_str: str,
    stop_time_str: str,
) -> tuple[dict[str, str | int | float], ...]:
    """Read calendar events in the time window from the public calendar url."""
    # Download the calendar file
    calendar_url = calendar_url.replace("webcal://", "https://")
    calendar_file = get(calendar_url, timeout=CALENDAR_REQUEST_TIMEOUT).text

    if "PRODID" not in calendar_file:
        calendar_file = _insert_prodid(calendar_file, APPLE_PRODID)

    if not calendar_file:
        return tuple([])

    # Parse the calendar file
    calendar = Calendar(calendar_file)

    # Get local timezone
    local_tz = tz.tzlocal()

    # Convert Unix timestamps to datetime
    start_time = datetime.fromtimestamp(int(start_time_str))
    stop_time = datetime.fromtimestamp(int(stop_time_str))

    start_time = start_time.replace(tzinfo=local_tz)
    stop_time = stop_time.replace(tzinfo=local_tz)

    # Filter and print events
    return tuple(
        {
            "name": event_.name,
            "begin": event_.begin.timestamp(),  # Convert to Unix timestamp
            "end": event_.end.timestamp(),  # Convert to Unix timestamp
        }
        for event_ in calendar.events
        if event_.begin.datetime >= start_time and event_.begin.datetime <= stop_time
    )


def _calendars_events(
    start_time_str: str,
    stop_time_str: str,
    *calendar_urls: str,
) -> tuple[dict[str, str | int | float], ...]:
    """Loop through multiple public calendars and collect events in the time window."""
    return tuple(
        chain(
            *(
                events_
                for url_ in calendar_urls
                if (events_ := _calendar_events(url_, start_time_str, stop_time_str))
            )
        )
    )


def _calendars_events_json(start_time_str: str, stop_time_str: str, *calendar_urls: str) -> str:
    """Return public calendar events in the time window as json."""
    return json.dumps(_calendars_events(start_time_str, stop_time_str, *calendar_urls))


def report_calendar_events_between() -> None:
    """Report public calendar events in the time window as json."""
    events = _calendars_events_json(*sys.argv[1:])
    if events:
        print(events)


__all__ = ["report_calendar_events_between"]
