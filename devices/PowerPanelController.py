import sqlite3
import time
import logging

logger = logging.getLogger(__name__)

# PowerPanel Personal stores live UPS readings in its SQLite database,
# updated every ~3 seconds. No SNMP or network configuration required.
_DB = r"C:\Program Files (x86)\CyberPower PowerPanel Personal\assets\PPPE_Db.db"

# DeviceLog column meanings (confirmed from live data):
#   OutVolt  — output voltage, RMS volts
#   BatCap   — battery capacity, percent
#   BatRun   — estimated runtime remaining, minutes
#   PowSour  — power source: 0 = utility (on line), non-zero = battery


class PowerPanel:
    _CACHE_TTL = 2.0  # seconds — avoid redundant DB reads within one sample cycle

    def __init__(self, deviceName):
        self.deviceName = deviceName
        self._cache = None
        self._cache_time = 0.0

    def open(self):
        pass

    def close(self):
        pass

    def _row(self):
        now = time.monotonic()
        if self._cache is None or (now - self._cache_time) > self._CACHE_TTL:
            conn = sqlite3.connect(_DB)
            self._cache = conn.execute(
                "SELECT OutVolt, BatCap, BatRun, PowSour FROM DeviceLog ORDER BY id DESC LIMIT 1"
            ).fetchone()
            conn.close()
            self._cache_time = now
        return self._cache

    def getOutputVoltage(self, chNum, trigger=None):
        row = self._row()
        return float(row[0])

    def getBatteryCapacity(self, chNum, trigger=None):
        row = self._row()
        return float(row[1])

    def getBatteryRuntime(self, chNum, trigger=None):
        row = self._row()
        return float(row[2])

    def getOnLine(self, chNum, trigger=None):
        row = self._row()
        return 1.0 if row[3] == 0 else 0.0  # PowSour=0 means utility power
