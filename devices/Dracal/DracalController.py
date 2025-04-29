import sys
import subprocess

class Dracal():
    def __init__(self, SN:str):
        self.SN = SN

    def open(self):
        pass

    def close(self):
        #sys.exit(0)
        pass

    def getHumidity(self):
        try:
            self.p = subprocess.check_output(["dracal-usb-get","-s", self.SN,"-i","1"]).decode('utf-8')
        except subprocess.CalledProcessError:
            print("dracal-usb-get error")
            #sys.exit(1)

        fields = self.p.split(",")

        rh = float(fields[0])

        #print(rh)
        #self.p.kill()
        return rh


    def getTemp(self):
        try:
            self.p = subprocess.check_output(["dracal-usb-get","-s", self.SN,"-i","0"]).decode('utf-8')
        except subprocess.CalledProcessError:
            print("dracal-usb-get error")
            #sys.exit(1)

        fields = self.p.split(",")

        temp = float(fields[0])

        #print(temp)
        #self.p.kill()
        return temp
    
#d = Dracal("E14760")
#d.getHumidity()
#d.getTemp()