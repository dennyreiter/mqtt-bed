#!/usr/bin/python

import os
import subprocess
import paho.mqtt.client as mqtt

DEBUG=0

from config import *

VERSION = 0.8


class sertaBLEController:
    def __init__(self, addr, pretend=False):
        self.pretend = pretend
        self.addr = addr
        self.handle = "0x0020"
        self.commands = {
            "Flat Preset": "e5fe1600000008fe",
            "ZeroG Preset": "e5fe1600100000f6",
            "TV Preset": "e5fe1600400000c6",
            "Head Up Preset": "e5fe160080000086",
            "Lounge Preset": "e5fe1600200000e6",
            "Massage Head Add": "e5fe1600080000fe",
            "Massage Head Min": "e5fe160000800086",
            "Massage Foot Add": "e5fe160004000002",
            "Massage Foot Min": "e5fe160000000105",
            "Head and Foot Massage On": "e5fe160001000005",
            "Massage Timer": "e5fe160002000004",
            "Lift Head": "e5fe160100000005",
            "Lower Head": "e5fe160200000004",
            "Lift Foot": "e5fe160400000002",
            "Lower Foot": "e5fe1608000000fe",
        }
        if DEBUG:
            print("Initialized control for %s" % addr)

    def sendCommand(self, name):
        cmd = self.commands.get(name, None)
        if DEBUG:
            print("Readying command: %s" % cmd)
        if cmd is None:
            raise Exception("Command not found: " + name)

        for retry in range(3):
            if DEBUG:
                print("Sending BLE command: %s" % cmd)
            cmd_args = [
                "/usr/bin/gatttool",
                "-b",
                self.addr,
                "--char-write-req",
                "--handle",
                self.handle,
                "--value",
                cmd,
            ]
            if DEBUG:
                print(cmd_args)
            if self.pretend:
                (" ".join(cmd_args))
                res = 0
            else:
                res = subprocess.call(cmd_args)
            if DEBUG:
                print("BLE command sent")
            if res == 0:
                break
            else:
                if DEBUG:
                    print("BLE write error, retrying in 2 seconds")
                time.sleep(2)

        return res == 0


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if DEBUG:
        print("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(MQTT_TOPIC + "/#")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    if DEBUG:
        print(msg.topic + " " + str(msg.payload))
    if DEBUG:
        print("Executing BLE command: " + str(msg.payload))
    ble = userdata
    ble.sendCommand(msg.payload)


def main():

    ble_address = os.environ.get("BLE_ADDRESS", BED_ADDRESS)
    pretend = os.environ.get("BLE_PRETEND", "false").lower() == "true"

    if ble_address is None:
        raise Exception("BLE_ADDRESS env not set")

    ble = sertaBLEController(ble_address, pretend)

    client = mqtt.Client(userdata=ble)
    client.on_connect = on_connect
    client.on_message = on_message

    client.username_pw_set(MQTT_USERNAME, password=MQTT_PASSWORD)
    client.connect(MQTT_SERVER, MQTT_SERVER_PORT, 60)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    client.loop_forever()


if __name__ == "__main__":
    main()
