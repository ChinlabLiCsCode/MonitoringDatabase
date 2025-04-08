# Don't Panic

This document explains how to use the Lithium-Cesium lab monitoring software which includes deviceManager.py, influxdb.py, and heimdall.py. The software enables data collection form various devices and uploads that data to an influxdb server where it can then be visualized with grafana

Also make sure that you've changed the main server config to set which devices are on and to add any new devices

# How it works:

## deviceManager.py
The deviceManager.py file contains a class DeviceManager with following parameters

1. deviceType: This is the general name for a device - ex: TSP01
2. deviceName: This is the specific name assigned to a device - ex: TSP1
3. configNum: This value specifies the config file bein used
4. queue: this is the multiprocessing queue that the collected data is being sent to

The first three parameters should match what is specified in the main server config so that the deviceManager can find the correct config file and device driver. This means that if the path to your device driver and config file are:

    /devices/TSP01/TSP01Controller.py
    /configfiles/TSP01Configs/TSP1Configs/TSP1Config1.yml

The deviceType should be TSP01, the deviceName should be TSP1 and the configNum should be 1

Once an instance of the DeviceManager class has been created, the program creates an instance of the device driver and reads the device's config file.

This class contains functions to open and close the device, and start and stop data collection.

Data collection is done using multithreading which gets a data value from the device and formats it for upload according to the parameters specified in the device config file. 

## Influxdb.py
The influxdb.py file contains a class InfluxDBLogger which creates a multiprocessing queue where all data is collected for upload. The credentials for uploading to influxdb are stored in a json file

    influxdb_credentials.json

which is located in the config files folder

This class has no input parameters and just contains functions for starting and stopping the logging loop.

The actual logging loop is run using multithreading and periodically pulls and writes data to influxdb with an upload time defined by the json file

## heimdall.py
The heimdall.py file contains a class ServerManager which creates multiple instances of the DeviceManager class and runs each instance's data collection function using muliprocessing. 

The class contains functions for starting and stopping all devices, starting and stopping specific devices, listing all active devices, refreshing devices if changes to the config file are made, and shutting down the program.

The class is formatted as an rpyc service so you can rpyc into it to access the above functions

https://rpyc.readthedocs.io/en/latest/tutorial/tut3.html

# How to add a new device
To add a new device to be monitored you only need a config file that specifies information about the device and a [deviceType]Controller.py file that directly communicates with it.

## config file
The config file should be a .yml file formatted in the following way:


    SN: "Serial Number"

    deviceType: "deviceType"

    location: "location"

    bucket: "bucket name"

    sampleRate: sample-rate

    parameters:
        parameter 1:
            isOn: True
            measurement: "measurment + units"
        
        parameter 2:
            isOn:
            chNum:
            measurement:
        .
        .
        .

        parameter n:
            isOn: 
            measurement:

The parameters should be a dictionary containing the function names being called. For example, if your device driver has a function called getMainTemp, then one of the parameters should be MainTemp with the mearement being "Temperature (units)"

The code filters out any integers from the parameter names so if your device has multiple channels and your driver has a function getChValue() then your parameter name should be Ch1Value and so on. To avoid errors your parameter should also include an entry called chNum which specified the channel being called

## device driver
The device driver is a python file with the name [deviceType]Controller.py where [deviceType] is the general name -ex: TSP01.

The driver should contain a class with the same name as the deviceType. This class should have open and close functions aswell as getValue functions that match the parameters in the config file

# Influxdb
Here is a link to the influxdb documentation:

[InfluxDB Documentation](https://docs.influxdata.com/influxdb/v2/)

# Grafana
here is a link to the grafana documentation:

[Grafana Documentation](https://grafana.com/docs/grafana/latest/)