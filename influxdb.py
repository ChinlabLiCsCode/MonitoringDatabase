import threading
from multiprocessing import Queue
from time import sleep

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException

import json
import logging
from dataclasses import dataclass
import os

INFLUXDB_CREDENTIAL_STORE_FILENAME = "influxdb_credentials.json"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@dataclass
class InfluxDBCredentials:
    url: str = "http://localhost:8086"
    org: str = "my-org"
    token: str = "my-token"
    uploadRate: str = "server-upload-rate"

def saveCredentials(credentials: InfluxDBCredentials) -> None:
    """Save the credentials to disk."""
    filename = os.path.join(os.environ['YBCONFIG'], INFLUXDB_CREDENTIAL_STORE_FILENAME)
    with open(filename, "w") as f:
        json.dump(
            {
                "url": credentials.url,
                "org": credentials.org,
                "token": credentials.token,
                "uploadRate": credentials.uploadRate
            },
            f,
            indent=2,
        )
    logger.info(f"Saved InfluxDB credentials to {filename}")

def restoreCredentials() -> InfluxDBCredentials:
    """When the server starts, it tries to restore the credentials."""
    filename = os.path.join(os.environ['YBCONFIG'], INFLUXDB_CREDENTIAL_STORE_FILENAME)
    try:
        with open(str(filename), "r") as f:
            data = json.load(f)
        return InfluxDBCredentials(
            url=data["url"],
            org=data["org"],
            token=data["token"],
            uploadRate=data["uploadRate"]
        )
    except FileNotFoundError:
        return InfluxDBCredentials()
    except json.JSONDecodeError:
        logger.error(f"Credentials file {filename} was corrupted.")
        return InfluxDBCredentials()

class InfluxDBLogger:
    def __init__(
        self
    ) -> None:
        
        self.isLogging = False
        self.credentials = restoreCredentials()
        self.updateConnection()

        #create queue for storing data
        self.queue = Queue()

    @property
    def credentials(self) -> InfluxDBCredentials:
        return self._credentials

    @credentials.setter
    def credentials(self, value: InfluxDBCredentials) -> None:
        self._credentials = value
        saveCredentials(value)

    def updateConnection(self):
        client = influxdb_client.InfluxDBClient(
            url=self.credentials.url,
            token=self.credentials.token,
            org=self.credentials.org,
        )
        self.write_api = client.write_api(write_options=SYNCHRONOUS)
    
    def startLogging(self):
        conn_success, message = self.testConnection()
        self.thread = threading.Thread(target=self.loggingLoop, daemon=True)
        if conn_success:
            self.isLogging = True
            self.thread.start()
            print("Started Logging")
        else:
            raise ConnectionError(f"Failed to connect to InfluxDB database: {message}")

    def stopLogging(self):
        self.isLogging = False
        self.thread.join()
        print("Stopped Logging")
    
    def loggingLoop(self):
        while self.isLogging:
            try:
                while not self.queue.empty():
                    self.data = self.queue.get()
                    print(self.data)
                    self.writeData(self.data)
                sleep(self.credentials.uploadRate)
            except Exception as e:
                print("Error with logging")
                print(e)
    
    def testConnection(self) -> tuple[bool, str]:
        """Write empty data to the server to test the connection"""
        client = influxdb_client.InfluxDBClient(
            url=self.credentials.url,
            token=self.credentials.token,
            org=self.credentials.org,
        )

        health = client.health()
        message = health.message
        success = health.status == "pass"
        if success:
            try:
                self.write_api.write(
                    bucket="testing",
                    org=self.credentials.org,
                    record={
                        "measurement": 'test',
                        "fields": {"Test Value": 3.14}
                    },
                )
            except ApiException as e:
                success = False
                message = e.message
            except Exception:
                success = False
                message = "Exception occurred. Check server log file for details."

        return success, message

    def writeData(self, entry: dict):
        """Write data to the database"""
        self.write_api.write(
            bucket=list(entry.keys())[0],
            org=self.credentials.org,
            record=entry[list(entry.keys())[0]],
            write_precision="s"
        )