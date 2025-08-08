import nidaqmx
from nidaqmx.constants import Edge, AcquisitionType, TerminalConfiguration

class NiDaq():
    """
    Class for reading data from an NiDaq
    """

    def __init__(self, deviceName):
        self.deviceName = deviceName

    def open(self):
        pass

    def close(self):
        if self.task is not None:
            self.task.close()

    def getChVoltage(self, ch:int, trigger:str):
        """
        Function for actually reading the data

        Parameters:
            ch: channel number (int)
            trigger: terminal source for digital triggering (str)

        returns:
            voltage: value in volts
        """

        if trigger is not None:
            #create the task and add the specified channel
            self.task = nidaqmx.Task()

            self.task.ai_channels.add_ai_voltage_chan((self.deviceName + "/ai" + str(ch-1)), min_val=-10, max_val=10, terminal_config=TerminalConfiguration.RSE)

            #define the trigger and sample clock
            self.task.triggers.start_trigger.cfg_dig_edge_start_trig(trigger_source=trigger, trigger_edge=Edge.RISING)

            self.task.timing.cfg_samp_clk_timing(
                rate=1e3,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=2
            )

            #get the voltage
            voltage = self.task.read()

            #close the task to free up resources
            self.task.close()
            self.task=None

            #return the voltage
            return voltage
        
        elif trigger is None:
            #create the task and add the specified channel
            self.task = nidaqmx.Task()

            self.task.ai_channels.add_ai_voltage_chan((self.deviceName + "/ai" + str(ch-1)), min_val=-10, max_val=10, terminal_config=TerminalConfiguration.RSE)

            #get the voltage
            voltage = self.task.read()

            #close the task to free up resources
            self.task.close()
            self.task=None

            #return the voltage
            return voltage