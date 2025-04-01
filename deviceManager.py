#imports
import os
import time
import threading
import importlib
import yaml
from yaml.loader import FullLoader
import multiprocessing

class DeviceManager(multiprocessing.Process):
    def __init__ (self, deviceType:str, deviceName:str, configNum:int, queue):
        """
        Class for controlling and collecting data from a device
            deviceType: the general name of the device - ex: TSP01, DP832, etc...
            deviceName: the specific name of the device - ex: TSP1
            configNum: the config file being used for this device
            queue: the multiprocessing queue that the data is being sent to
        """

        self.deviceName = deviceName
        self.deviceType = deviceType
        self.configNum = configNum

        #get the device class for controling the device
        self.DeviceClass = getattr(importlib.import_module("devices." + self.deviceType + "." + self.deviceType + "Controller"), self.deviceType )

        #get the config folder path variable
        self.ybConfig = os.environ["YBCONFIG"]

        #List containing all data from all devices
        self.serverData = queue

        self.isCollecting = threading.Event()

        #read Main Config
        self.readDeviceConfig()

        #initialize the device
        self.device = self.DeviceClass(self.serialNum)

    def readDeviceConfig(self):
        """
        Read the config file for this device
        """

        #assemble file path
        self.filepath = os.path.join(self.ybConfig, (self.deviceType + "Configs"), (self.deviceName + "Configs") ,(self.deviceName + "Config" + str(self.configNum) + ".yml"))

        #open the config file
        try:
            with open(self.filepath) as f:
                self.deviceConfig = yaml.load(f, Loader=FullLoader)
        except Exception as e:
            print("Failed to read config file for " + self.deviceName)
            print(e)
            exit()

        #get device info
        self.serialNum = self.deviceConfig["SN"]
        self.bucket = self.deviceConfig["bucket"]
        self.sampleRate = self.deviceConfig["sampleRate"]
        self.deviceParameters = self.deviceConfig["parameters"]
        
    def openDevice(self):
        """
        Function for opening a device
        """

        if self.device is not None:
            self.device.open()
            print("Opened " + self.deviceName)
        else:
            try:
                self.device = self.DeviceClass(self.serialNum)
                self.device.open()
                print("Opened " + self.deviceName)

            except Exception as e:
                print("Error, unable to open device " + self.deviceName)
                print(e)

    def closeDevice(self):
        """
        Function for closing a device
        """
        self.device.close()
        self.device = None
        print("Closed device " + self.deviceName)

    def getData(self):
        try:
            self.deviceData = {}
            for parameter in self.deviceParameters:
                #filter out any integers so that gettatr works
                methodCall = ''.join([i for i in parameter if not i.isdigit()])

                if self.deviceParameters[parameter]["isOn"]:
                    if "chNum" not in self.deviceParameters[parameter].keys():
                        self.deviceData.update(
                            {parameter: {
                            "measurement": self.deviceParameters[parameter]["measurement"],

                            "tags": {"Device_Class": self.deviceType, "Serial_Number": self.serialNum, "Parameter": parameter},

                            "fields": {self.deviceParameters[parameter]["measurement"]: getattr(self.device, 'get' + methodCall)()},

                            "time": int(time.time())
                            }}
                        )
                    else:
                        chNum = self.deviceParameters[parameter]["chNum"]
                        self.deviceData.update(
                            {(parameter): {
                            "measurement": self.deviceParameters[parameter]["measurement"],

                            "tags": {"Device_Class": self.deviceType, "Serial_Number": self.serialNum, "Parameter": parameter},

                            "fields": {self.deviceParameters[parameter]["measurement"]: getattr(self.device, 'get' + methodCall)(chNum)},

                            "time": int(time.time())
                            }}
                        )
        except Exception as e:
            print("Error, unable to get data from, " + self.serialNum)
            self.isCollecting.clear()
            print(e)

    def collectData(self):
        while self.isCollecting.is_set():
            counter = 0
            if counter % self.sampleRate == 0:
                try:
                    self.getData()
                    for value in self.deviceData:
                        self.rawData = {self.bucket: self.deviceData[value]}
                        self.serverData.put(self.rawData)
                except Exception as e:
                    print("Error, stopped collecting data")
                    print(e)
                    self.isCollecting.clear()

            counter += 1
            time.sleep(1) #make value specific to each device

    def startServer(self):
        """
        Opens the device and starts data collection thread
        """
        self.run()

    def run(self):
        self.openDevice()
        self.isCollecting.set()

        self.thread = threading.Thread(target = self.collectData)
        self.thread.start()

        print("Started server for " + self.deviceName)
    
    def stopServer(self):
        """
        Stops data collection and closes the device
        """
        self.isCollecting.clear()

        self.thread.join()

        print("Stopped " + self.deviceName + " server")

        self.closeDevice()
