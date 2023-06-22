from .event import Event as Event


class Calendar:
    events: list[Event]

    def __init__(self, imports: str = ...) -> None: ...
