# Control mpv from a calendar

mpv-calendar is a python package that installs an always-on digital display onto a Linux machine (e.g. a raspberry pi). The content on the display can be scheduled with your normal calendar app by creating a public calendar and registering its url with the app. There is also a web interface for more immediate control.

To install in one go, run this command:
```bash
curl -sL 'https://github.com/Studio45sf/mpv-cal/-/raw/main/src/mpv_calendar/scripts/mpv-calendar-remote-installer' | bash -
```

Create a file at `~/.config/mpv/calendars` on the target machine with a list of the calendars to watch for events. Simply put a url or file path as the title of the event.

## Caveats
- Linux only
- Takes over your display
- No other mpv instances are allowed, they will be killed throughout the life cycle of the app

## What is installed?

The installation includes a python package installed via pip and 4 services installed via systemd:
1. mpv-calendar-watcher.service: watches the list of calendars in `~/.config/mpv/calendars` for new streaming events
2. mpv-calendar-viewer.service: an mpv instance with appropriate settings
3. mpv-calendar-controller.service: a web front end for controlling mpv
4. nginx.service: http and rtmp server for receiving streams that can be viewed by mpv

# Roadmap and todos
- [ ] when a link can’t be directly read by youtube-dl/mpv, curl/wget/aria2c/scraper should be employed to download the content
- [ ] background stream that always loops instead of using a default video for looping
- [ ] loop support in the foreground stream via description (parsing description in general)
- [ ] xdotool should be used to check that mpv is actually open on the target display and use that as a systemd restart condition. It’s been observed that the mpv process can persist even if the window crashes.
- [ ] when given a bad link, mpv crashes. systemd service helps here, but could be handled in lua.
- [ ] systemd restart on viewer has a bug where by it does not kill the mpv process correctly
- [ ] web interface should have button for rebooting the system
- [ ] web interface should have access controls
- [ ] web interface should publish a domain name on the local network or be discoverable
- [ ] web interface should have previous/back button
- [ ] matrix/sms/email notifier channels
- [ ] public access for debugging (onion service or ssh tunnel)
- [ ] web interface should show the current playlist state
- [ ] separate audio stream
- [ ] joined audio stream / non-muted
- [ ] mic input
- [ ] web cam input
