import serial


class AgilentIonPump:
    """Driver for the Agilent 4UHV ion pump controller (Window Protocol).

    Serial: 9600 baud, 8 data bits, no parity, 1 stop bit.
    """

    STX, ETX = 0x02, 0x03
    ACK, NACK = 0x06, 0x15
    UNKNOWN_WIN, DATA_TYPE_ERR, OUT_OF_RANGE = 0x32, 0x33, 0x35

    def __init__(self, port, addr=0, timeout=1):
        self.ser = serial.Serial(port, 9600, bytesize=8,
                                 parity='N', stopbits=1, timeout=timeout)
        self.addr = 0x80 + addr  # RS-232: leave addr=0
    
    def open(self):
        pass
        

    # --- protocol ---------------------------------------------------------

    def _crc(self, payload: bytes) -> bytes:
        c = 0
        for b in payload:
            c ^= b
        return f"{c:02X}".encode("ascii")

    def read_window(self, win: int) -> str:
        win_s = f"{win:03d}".encode("ascii")
        body = bytes([self.addr]) + win_s + b"0" + bytes([self.ETX])  # '0' = read
        msg = bytes([self.STX]) + body + self._crc(body)
        self.ser.write(msg)
        return self._parse(self.ser.read(64))

    def write_window(self, win: int, data: str) -> str:
        win_s = f"{win:03d}".encode("ascii")
        body = bytes([self.addr]) + win_s + b"1" + data.encode("ascii") + bytes([self.ETX])
        msg = bytes([self.STX]) + body + self._crc(body)
        self.ser.write(msg)
        return self._parse(self.ser.read(64))

    def _parse(self, resp: bytes) -> str:
        if not resp:
            raise IOError("no response from controller")

        # single-byte status replies (ACK / NACK / errors) sit right after ADDR
        if len(resp) >= 3 and resp[2] in (
            self.ACK, self.NACK, self.UNKNOWN_WIN,
            self.DATA_TYPE_ERR, self.OUT_OF_RANGE,
        ):
            code = resp[2]
            if code == self.ACK:
                return "ACK"
            names = {
                self.NACK: "NACK (command failed)",
                self.UNKNOWN_WIN: "unknown window",
                self.DATA_TYPE_ERR: "data type error",
                self.OUT_OF_RANGE: "out of range / window disabled",
            }
            raise IOError(f"controller returned {names[code]}")

        # data reply: STX ADDR WIN(3) COM DATA ETX CRC...
        try:
            etx = resp.index(self.ETX)
        except ValueError:
            raise IOError("malformed response (no ETX)")
        return resp[6:etx].decode("ascii", errors="ignore").strip()

    # --- channel readouts -------------------------------------------------

    # window layout is regular: base = 810 + (ch-1)*10
    #   +0 = V measured, +1 = I measured, +2 = pressure
    def _base(self, ch: int) -> int:
        if ch not in (1, 2, 3, 4):
            raise ValueError("channel must be 1-4")
        return 810 + (ch - 1) * 10

    def getChVoltage(self, ch: int, trigger=None) -> int:
        """Measured voltage on a channel, in volts."""
        return int(self.read_window(self._base(ch) + 0))

    def getChCurrent(self, ch: int, trigger=None) -> float:
        """Measured current on a channel, in amps (e.g. '1E-10' -> 1e-10)."""
        return float(self.read_window(self._base(ch) + 1))

    def getChPressure(self, ch: int, trigger=None) -> float:
        """Measured pressure on a channel. Returns 0.0 if the controller reports
        a non-numeric status (e.g. 'Low Pressure' when below the gauge range)."""
        raw = self.read_window(self._base(ch) + 2)
        try:
            return float(raw)
        except ValueError:
            return 0.0

    # --- convenience ------------------------------------------------------

    def get_all_voltages(self) -> dict:
        return {ch: self.getChVoltage(ch) for ch in (1, 2, 3, 4)}

    def get_all_currents(self) -> dict:
        return {ch: self.getChCurrent(ch) for ch in (1, 2, 3, 4)}

    def get_all_pressures(self) -> dict:
        return {ch: self.getChPressure(ch) for ch in (1, 2, 3, 4)}

    def get_unit(self) -> str:
        """Pressure unit currently configured on the controller."""
        return {"0": "Torr", "1": "mBar", "2": "Pa"}.get(
            self.read_window(600), "unknown")

    def close(self):
        self.ser.close()


if __name__ == "__main__":
    pump = AgilentIonPump("COM3")
    print("Pressure unit:", pump.get_unit())
    for ch in (1, 2):
        print(f"CH{ch}: {pump.getChVoltage(ch)} V, "
              f"{pump.getChCurrent(ch):.2e} A, "
              f"{pump.getChPressure(ch):.2e}")
    pump.close()