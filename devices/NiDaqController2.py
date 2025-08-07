import nidaqmx
from nidaqmx.constants import Edge, AcquisitionType, TerminalConfiguration

class NiDaq():
    """
    Class for reading data from an NiDaq
    """

    def __init__(self, deviceName, *args):
        self.deviceName = deviceName
        self.parameters = args[0]['paramters']

        #generate the list non triggered tasks, list of distinct triggers and the dictionary of channel numbers with assigned triggers
        self.listOfUntriggeredTasks = []
        self.listofDistinctTriggers = []
        self.dictOfAssignedTriggers = {}

        for param in self.parameters:
            if self.parameters[param]['isOn'] and not self.parameters[param]['triggered']:
                #add the channel number to the list of untriggered tasks
                self.listOfUntriggeredTasks.append(self.parameters[param]['chNum'])

            elif self.parameters[param]['isOn'] and self.parameters[param]['triggered']:
                #add channel number and trigger to dictionary
                self.dictOfAssignedTriggers[self.parameters[param]['chNum']] = self.parameters[param]['trigger']

                #add the trigger to the list of triggers if not already there
                if self.parameters[param]['trigger'] not in self.listofDistinctTriggers:
                    self.listofDistinctTriggers.append(self.parameters[param]['trigger'])

    def open(self):
        """
        Create 1 task for all of the non triggered channels and a unique task for all of the triggered ones
        """

        #create an untriggered task if the list of untriggered tasks isn't empty
        if len(self.listOfUntriggeredTasks) != 0:
            try:
                self.untriggeredTask = nidaqmx.Task()
                self.untriggeredTasksActive = True # boolean to check if there are any untriggered tasks
            except Exception as e:
                print("Error creating untriggered tasks: " + e)
        
        self.triggeredTasks  = {} #dictionary for storing all triggered tasks

        #create a set of triggered tasks for each distinct trigger and add them to the dictionary if there are triggered tasks
        if len(self.listofDistinctTriggers) != 0:
            self.triggeredTasksActive = True
            for trigger in self.listofDistinctTriggers:
                try:
                    self.triggeredTasks[trigger] = nidaqmx.Task()
                except Exception as e:
                    print("Error creating triggered task: " + e)

        #add channels to the tasks
        for param in self.parameters:
            chNum = self.parameters[param]['chNUm']

            if self.untriggeredTasksActive and chNum in self.listOfUntriggeredTasks:
                try:
                    self.untriggeredTask.ai_channels.add_ai_voltage_chan((self.deviceName + "/ai" + str(chNum)), min_val=-10, max_val=10, terminal_config=TerminalConfiguration.RSE)
                
                except Exception as e:
                    print("Error adding channel" + str(chNum) + ": " + e)
            
            elif self.triggeredTasksActive and chNum in self.dictOfAssignedTriggers:
                trigger = self.parameters[param]["trigger"]

                try:
                    #add the channel to the correct triggered task
                    self.triggeredTasks[trigger].ai_channels.add_ai_voltage_chan((self.deviceName + "/ai" + str(chNum)), min_val=-10, max_val=10, terminal_config=TerminalConfiguration.RSE)

                    #set the trigger
                    self.triggeredTasks[trigger].triggers.start_trigger.cfg_dig_edge_start_trig(trigger_source=trigger, trigger_edge=Edge.RISING)

                    #set the timming
                    self.triggeredTasks[trigger].timing.cfg_samp_clk_timing(
                        rate=1e3,
                        sample_mode=AcquisitionType.FINITE,
                        samps_per_chan=2
                    )
                except Exception as e:
                    print("Error adding triggered channel" + str(chNum) + ": " + e)

    def close(self):
        """
        close tasks to free up resources
        """
        if self.untriggeredTask is not None:
            self.untriggeredTask.close()
        
        else:
            print("Untriggered tasks are already closed")
        
        for task in self.triggeredTasks:
            if self.triggeredTasks[task] is not None:
                self.triggeredTasks[task].close()
            
            else:
                print('Triggered task is already closed')

    def getChVoltage(self, ch:int, trigger:str, triggered:bool):
        """
        Function for actually reading the data

        Parameters:
            ch: channel number (int)
            trigger: terminal source for digital triggering (str)

        returns:
            chVoltage: value in volts
        """

        if triggered: #read voltages for triggered channels
            try:
                voltages = self.triggeredTasks[trigger].read()

                #get the channel index
                chIndex = self.listOfUntriggeredTasks.index(ch)
                
                #read the voltage that's been specified
                chVoltage = voltages[chIndex]
                return chVoltage
            except Exception as e:
                print("Error reading volate for channel " + str(ch) + ": " + e)

        elif triggered == False: #read voltages for untriggered channels
            try:
                voltages = self.untriggeredTask.read()

                #get the channel index
                chIndex = self.listOfUntriggeredTasks.index(ch)
                
                #read the voltage that's been specified
                chVoltage = voltages[chIndex]
                return chVoltage

            except Exception as e:
                print("Error reading voltage for channel " + str(ch) + ": " + e)
