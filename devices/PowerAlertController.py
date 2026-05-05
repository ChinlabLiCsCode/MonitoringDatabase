import logging
from pysnmp.hlapi import (
    getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity,
)

logger = logging.getLogger(__name__)

# Tripp Lite PowerAlert SNMP agent — runs locally on Windows.
# Enable SNMP in PowerAlert: go to PowerAlert → Settings → SNMP,
# enable the agent, set community string to "public", port 161.
_HOST      = "127.0.0.1"
_PORT      = 161
_COMMUNITY = "public"

# Standard UPS MIB (RFC 1628 — 1.3.6.1.2.1.33), supported by Tripp Lite.
_OID_INPUT_VOLTAGE    = "1.3.6.1.2.1.33.1.3.3.1.3.1"  # upsInputVoltage, RMS volts
_OID_BATTERY_CAPACITY = "1.3.6.1.2.1.33.1.2.5.0"      # upsEstimatedChargeRemaining, percent
_OID_BATTERY_RUNTIME  = "1.3.6.1.2.1.33.1.2.4.0"      # upsEstimatedMinutesRemaining, minutes
_OID_OUTPUT_LOAD      = "1.3.6.1.2.1.33.1.4.4.1.5.1"  # upsOutputPercentLoad, percent
_OID_OUTPUT_SOURCE    = "1.3.6.1.2.1.33.1.4.1.0"      # upsOutputSource: 2=normal, 3=battery


class PowerAlert:
    def __init__(self, deviceName):
        self.deviceName = deviceName

    def open(self):
        pass

    def close(self):
        pass

    def _get(self, oid):
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(
                SnmpEngine(),
                CommunityData(_COMMUNITY, mpModel=1),  # SNMPv2c
                UdpTransportTarget((_HOST, _PORT), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
            )
        )
        if errorIndication:
            raise RuntimeError(f"SNMP error: {errorIndication}")
        if errorStatus:
            raise RuntimeError(f"SNMP error: {errorStatus.prettyPrint()} at index {errorIndex}")
        return varBinds[0][1]

    def getInputVoltage(self, chNum, trigger=None):
        return float(self._get(_OID_INPUT_VOLTAGE))

    def getBatteryCapacity(self, chNum, trigger=None):
        return float(self._get(_OID_BATTERY_CAPACITY))

    def getBatteryRuntime(self, chNum, trigger=None):
        return float(self._get(_OID_BATTERY_RUNTIME))  # already in minutes

    def getOutputLoad(self, chNum, trigger=None):
        return float(self._get(_OID_OUTPUT_LOAD))

    def getOnLine(self, chNum, trigger=None):
        status = int(self._get(_OID_OUTPUT_SOURCE))
        return 1.0 if status == 2 else 0.0  # 1.0 = on mains, 0.0 = on battery
