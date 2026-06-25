import subprocess

class Dracal():
    def __init__(self, name):
        pass

    def open(self):
        pass

    def close(self):
        pass

    def getChHume(self, chNum:str, trigger=None):
        "chNum is the serial number of the device"
        self.SN = chNum

        try:
            self.p = subprocess.check_output(["dracal-usb-get","-s", self.SN,"-i","1"]).decode('utf-8')
        except subprocess.CalledProcessError:
            print(f"Can't get Humidity for {chNum}")
            raise

        fields = self.p.split(",")

        rh = float(fields[0])
        return rh


    def getChTemp(self, chNum:str, trigger=None):
        "ChHum is the serial number of the device"
        self.SN = chNum

        try:
            self.p = subprocess.check_output(["dracal-usb-get","-s", self.SN,"-i","0"]).decode('utf-8')
        except subprocess.CalledProcessError:
            print(f"Can't get Temperature for {chNum}")
            raise

        fields = self.p.split(",")

        temp = float(fields[0])
        return temp

