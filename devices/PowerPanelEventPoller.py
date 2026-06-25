import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime

from influxdb_client import WritePrecision

logger = logging.getLogger(__name__)

_DB = r"C:\Program Files (x86)\CyberPower PowerPanel Personal\assets\PPPE_Db.db"

_CATEGORY_LABELS = {
    "I": "Input",
    "O": "Output",
    "B": "Battery",
    "D": "Device",
    "C": "Communications",
    "H": "Hardware",
    "E": "Environment",
}


class PowerPanelEventPoller:
    """
    Polls the PowerPanel Personal SQLite EventLog for new UPS events and writes
    them to InfluxDB with their original timestamps.  Runs as a daemon thread
    alongside the main Heimdall logging loop.
    """

    def __init__(self, influx_logger, bucket: str = "mainLab", poll_interval: float = 5.0):
        self._influx = influx_logger
        self._bucket = bucket
        self._poll_interval = poll_interval
        self._last_id = self._load_state()
        self._running = False
        self._thread = None

    # ── state persistence ─────────────────────────────────────────────────────

    @property
    def _state_path(self) -> str:
        configs_dir = os.environ.get("DatabaseDevelopmentConfigs", ".")
        return os.path.join(configs_dir, "ups_event_state.json")

    def _load_state(self) -> int:
        try:
            with open(self._state_path) as f:
                return json.load(f).get("last_event_id", 0)
        except (FileNotFoundError, json.JSONDecodeError):
            return 0

    def _save_state(self, last_id: int):
        with open(self._state_path, "w") as f:
            json.dump({"last_event_id": last_id}, f)

    # ── thread control ────────────────────────────────────────────────────────

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="PowerPanelEventPoller")
        self._thread.start()
        logger.info("PowerPanel event poller started (last_id=%d)", self._last_id)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)

    def _loop(self):
        while self._running:
            try:
                self._poll()
            except Exception:
                logger.exception("Error polling PowerPanel EventLog")
            time.sleep(self._poll_interval)

    # ── polling logic ─────────────────────────────────────────────────────────

    def _poll(self):
        conn = sqlite3.connect(_DB)
        try:
            rows = conn.execute(
                """
                SELECT e.id, e.EventId, e.CreateTime, e.Duration,
                       en.description, en.category
                FROM EventLog e
                LEFT JOIN EventEnum en ON e.EventId = en.number
                WHERE e.id > ?
                ORDER BY e.id ASC
                """,
                (self._last_id,),
            ).fetchall()
        finally:
            conn.close()

        if not rows:
            return

        local_tz = datetime.now().astimezone().tzinfo
        points = []
        max_id = self._last_id

        for row_id, event_id, create_time, duration, description, category in rows:
            dt = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=local_tz)
            points.append({
                "measurement": "UPS Events",
                "time": dt,
                "tags": {
                    "device": "UPS1",
                    "category": _CATEGORY_LABELS.get(category, category or "Unknown"),
                },
                "fields": {
                    "event_id": event_id,
                    "description": description or f"Event {event_id}",
                    "duration_s": float(duration or 0),
                },
            })
            max_id = row_id

        self._influx.write_api.write(
            bucket=self._bucket,
            org=self._influx.credentials.org,
            record=points,
            write_precision=WritePrecision.MS,
        )
        self._last_id = max_id
        self._save_state(max_id)
        logger.info("Wrote %d UPS event(s) to InfluxDB", len(points))
        for p in points:
            print(f"[UPS Event] {p['fields']['description']} @ {p['time']}")
