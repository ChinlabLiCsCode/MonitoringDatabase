import subprocess

class Dracal():
    def __init__(self, name, trigger=None):
        pass

    def open(self):
        pass

    def close(self):
        pass

    def getChHume(self, chNum:str):
        "chNum is the serial number of the device"
        self.SN = chNum

        try:
            self.p = subprocess.check_output(["dracal-usb-get","-s", self.SN,"-i","1"]).decode('utf-8')
        except subprocess.CalledProcessError:
            print("dracal-usb-get error")
            message = "Can't get Humidity for " + chNum
            print(message)

        fields = self.p.split(",")

        rh = float(fields[0])
        return rh


    def getChTemp(self, chNum:str):
        "ChHum is the serial number of the device"
        self.SN = chNum

        try:
            self.p = subprocess.check_output(["dracal-usb-get","-s", self.SN,"-i","0"]).decode('utf-8')
        except subprocess.CalledProcessError:
            print("dracal-usb-get error")
            message = "Can't get Temperature for " + chNum
            print(message)


        fields = self.p.split(",")

        temp = float(fields[0])
        return temp

