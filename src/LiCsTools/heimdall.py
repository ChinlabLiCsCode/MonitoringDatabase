import os
import multiprocessing
import rpyc
from rpyc.utils.server import ThreadedServer
import yaml
from yaml.loader import FullLoader
from LiCsTools.influxdb import InfluxDBLogger
from LiCsTools.deviceManager import DeviceManager
from PowerPanelEventPoller import PowerPanelEventPoller

class ServerManager(rpyc.Service):
    """
    Class for managing all device managers, collects data from all active devices and periodically uploads to influxDB
    """
    def __init__(self):
        self.deviceConfigs = os.environ["DatabaseDevelopmentConfigs"]
        self.isServerActive = False

        #read the server config file
        self.readServerConfig()

        #initinalize influxdb class
        self.influx = InfluxDBLogger()

        #init all active device servers
        self.initServerManager()

        #start server
        self.exposed_activateServers()

    def readServerConfig(self):
        """
        Reads server config file, collects influx database credentials and checks how many device servers are active
        """
        #assemble file path
        self.filepath = os.path.join(self.deviceConfigs,  "mainServerConfig.yml")

        #open the config file
        try:
            with open(self.filepath) as f:
                self.serverConfig = yaml.load(f, Loader=FullLoader)

                #get dictionary of device servers
                self.deviceList = self.serverConfig["devices"]
        except Exception as e:
            print("Failed to read server config file")
            print(e)
            exit()
        
        #check how many device servers are active
        self.checkNumDevices()

    def checkNumDevices(self):
        """
        Checks how many device servers are set to active by the config file
        """
        self.activeDevices = []

        for value in self.deviceList:
            if self.deviceList[value]["isOn"] == True:
                self.activeDevices.append(value)
        
        #print("There are/is, " + str(len(self.activeServers)) + "active device server(s)")
        #print(self.activeServers)

    def initServerManager(self):
        """
        Initialize each device and stores them in a deviceServers dictionary
        """
        self.deviceServers = {}
        #initilaize each devices
        for device in self.activeDevices:
            self.deviceType = self.deviceList[device]["deviceType"]
            self.deviceConfigNum = self.deviceList[device]["config"]
            self.deviceServers[device] = DeviceManager(deviceType=self.deviceType, deviceName =device, configNum=self.deviceConfigNum, queue=self.influx.queue)

    def exposed_listActiveServers(self):
        return self.servers
    
    def exposed_activateServers(self):
        """
        Run each device server as a process and stores those processes in a new dictionary
        """
        self.isServerActive = True

        #start all servers
        self.servers = {}
        for device in self.activeDevices:
            self.servers[device] = multiprocessing.Process(target=self.deviceServers[device].startServer)
            self.servers[device].run()
        print("Started All Servers")

        #start logging data
        self.influx.startLogging()

        #start UPS event poller
        if hasattr(self, "_event_poller") and self._event_poller is not None:
            self._event_poller.stop()
        self._event_poller = PowerPanelEventPoller(self.influx)
        self._event_poller.start()
    
    def exposed_stopAllServers(self):
        """
        Stops all servers
        """
        if len(self.activeDevices) !=0:
            for process in self.servers:
                try:
                    self.deviceServers[process].stopServer()
                
                except Exception as e:
                    print("Error: Failed to stop " + process)
                    print(e)

        self.isServerActive = False
        print("All device servers stopped")
    
    def exposed_refreshAllDevices(self):
        """
        Function for restarting server manager, stops all devices, refreshes list of active devices, reinits and restarts servers
        """
        #stop all servers
        self.exposed_stopAllServers()

        #reread the main config file
        self.readServerConfig()
        
        #check how many device servers are active 
        #self.checkNumDevices()

        #reinit servers
        self.initServerManager()

        #activate servers
        self.exposed_activateServers()

    def exposed_refreshDevice(self, deviceName):
        if deviceName in self.servers:
            self.exposed_stopDeviceServer(deviceName)
            self.deviceServers[deviceName].readDeviceConfig()
            self.exposed_startDeviceServer(deviceName)
        else:
            print("Error, " + deviceName + " is not active")

    def exposed_startDeviceServer(self, deviceName:str):
        """
        Starts a device server for a specific device - ex: TSP1
        """

        #refresh the list of active devices
        self.checkNumDevices()

        #restart the server if the server process still exists
        if deviceName in self.servers:
            self.deviceServers[deviceName].startServer()

        #else, initialize a new device and process
        elif deviceName in self.activeDevices:
            self.deviceType = self.deviceList[deviceName]["deviceType"]
            self.deviceConfigNum = self.deviceList[deviceName]["config"]
            self.deviceServers[deviceName] = DeviceManager(deviceType=self.deviceType, deviceName =deviceName, configNum=self.deviceConfigNum, queue=self.influx.queue)

            self.servers[deviceName] = multiprocessing.Process(target=self.deviceServers[deviceName].startServer)
            self.servers[deviceName].run()
        
        else:
            print("Error: " + deviceName + " not in deviceList")

    def exposed_stopDeviceServer(self,deviceName:str):
        """
        Function to stop a specific device server - ex:TSP1
        """
        if deviceName in self.servers:
            self.deviceServers[deviceName].stopServer()
            self.activeDevices.pop(self.activeDevices.index(deviceName))
        else:
            print("Error: " + deviceName + " not in deviceList")

    def exposed_shutdown(self):
        """
        Runs exposed_stopAllServers, clears dictionaries, and closes server manager
        """
        self.exposed_stopAllServers()

        #end all processes
        for process in self.activeDevices:
            self.servers[process].close()

        #stop UPS event poller
        if hasattr(self, "_event_poller") and self._event_poller is not None:
            self._event_poller.stop()

        #stop logging
        self.influx.stopLogging()
        
        #clear all dictionaries
        self.activeDevices.clear()
        self.deviceServers.clear()
        self.servers.clear()

        if self.isServerActive == False:
            try:
                server.close()
                print("Shutting down server manager")
                exit()
            except:
                pass

        else:
            print("Error: Server is still active")

def activate():
    global server 
    server = ThreadedServer(service=ServerManager(), port=18861)
    server.start()

if __name__ == "__main__":
    activate()