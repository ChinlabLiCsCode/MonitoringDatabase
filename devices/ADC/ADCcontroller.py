import mmap

class ADC():
    """Instrument driver for ADC.
    
    It just connects to the device via mmap and then reads the specified channel voltage"""

    def __init__(self, deviceName):
        self.deviceName = deviceName
    
    def open(self):
        try:
            "Initialize the device"
            self.analog = mmap.mmap(-1, 40, tagname='EECI_ADC12U12_OUT', access=mmap.ACCESS_READ)
        except:
            errorMsg = "Error: Make sure " + self.deviceName + " is connected "
            print(errorMsg)

    def close(self):
        if self.analog is not None:
            self.analog.close()
        else:
            print(self.deviceName, "is already closed")

    def getChVoltage(self, ch:int):
        "Return the specific channel voltage from the usb accounting for the fact that the ADC uses 256 bits"

        self.chVoltage = (self.analog[ch] - 240)*256 + self.analog[ch+12]
        return self.chVoltage       

