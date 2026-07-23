"""In-memory progress broker for streaming audit progress over SSE.

Events are kept per run so a subscriber that connects late replays the
full history before following live events. State lives in process memory
only: after a server restart the stream endpoint falls back to the run
status stored in the database.
"""

import threading

SUBSCRIBE_WAIT_SECONDS = 30.0


class ProgressBroker:
    def __init__(self):
        self._runs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def start(self, run_id: str) -> None:
        with self._lock:
            self._runs[run_id] = {
                "events": [],
                "done": False,
                "condition": threading.Condition(),
            }

    def _entry(self, run_id: str):
        with self._lock:
            return self._runs.get(run_id)

    def publish(self, run_id: str, event: dict, final: bool = False) -> None:
        entry = self._entry(run_id)
        if entry is None:
            return
        with entry["condition"]:
            entry["events"].append({"final": final, "data": event})
            if final:
                entry["done"] = True
            entry["condition"].notify_all()

    def subscribe(self, run_id: str):
        """Yield {final, data} events, replaying history first. The
        generator ends after the final event, or immediately for runs
        this process has never seen."""
        entry = self._entry(run_id)
        if entry is None:
            return
        index = 0
        while True:
            with entry["condition"]:
                if index >= len(entry["events"]):
                    if entry["done"]:
                        return
                    entry["condition"].wait(timeout=SUBSCRIBE_WAIT_SECONDS)
                events = list(entry["events"][index:])
                index += len(events)
            for event in events:
                yield event
                if event["final"]:
                    return
