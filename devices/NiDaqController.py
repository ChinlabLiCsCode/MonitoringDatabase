import nidaqmx

class NiDaq():
    """
    Instrument driver for the 8 channel NiDaq
    """
    
    def __init__(self, deviceName):
        self.deviceName = deviceName
    
    def open(self):
        """
        Creates a task and initializes all 8 channels
        """

        try:
            self.task = nidaqmx.Task()
            for i in range(8):
                self.task.ai_channels.add_ai_voltage_chan((self.deviceName + "/ai" + str(i)), min_val=-10, max_val=10)
            #print("Opened NiDaq: " + self.deviceName)
        except:
            print("Error: Make sure the device is connected")

    def close(self):
        """
        Closes task to free up resources
        """

        if self.task is not None:
            self.task.close()
            #print("Closed NiDaq: " + self.deviceName)
        else:
            print("Device is already closed")
    
    def getChVoltage(self, ch:int):
        """
        Reads voltages from all 8 channels but only returns the channel voltage specified
        """

        self.data = {}

        #read all voltages from device
        self.voltages = self.task.read()

        #add voltages to data dictionary
        for i in range(8):
            self.data[i+1] = self.voltages[i]
        
        #read the voltage that's been specified
        self.chVoltage = self.data[ch]
        return self.chVoltage
        