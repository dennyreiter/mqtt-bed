#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Created By  : https://github.com/mishnz
# Created Date: 14/01/2022
# version ='1.0'
# ---------------------------------------------------------------------------
""" DewertOkin HE150 controller module for mqtt-bed
https://github.com/karl0ss/mqtt-bed

I recently purchased a "Napp" https://napp.co.nz/ bed and mattress.
On arrival, the base is an "A.H. Beard" https://ahbeard.com/ base.
Digging into the internals the Bluetooth chips identify themselves as "Okin"
branded.

The controller unit as a whole is branded as a DewertOkin HE150
https://dewertokin.hu/termek/he-150/
The DewertOkin Android application for this is "Comfort Enhancement 2"
aka "Comfort Plus"
https://play.google.com/store/apps/details?id=com.dewertokin.comfortplus
Using this application I intercepted the Bluetooth codes.

I moved from the depreciated pygatt to bluepy due to connectivity issues.
The Bluetooth connection string for this bed uses "random" instead of
"public" like the other beds.
This module ended up being bigger than expected as the HE150 disconnects on a
lack of connectivity and on other unknown conditions.
The additional code manages a keepalive/heartbeat thread.

This module is more verbose than the others to aid in debugging.
Note: This module will work with some other "Okin"/"DewertOkin" models.

"""
# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import logging
import threading
import time

import bluepy.btle as ble


class dewertokinBLEController:
    def __init__(self, addr):
        self.logger = logging.getLogger(__name__)
        self.charWriteInProgress = False
        self.addr = addr
        self.manufacturer = "DerwentOkin"
        self.model = "A H Beard"
        self.commands = {
            "Flat Preset": "040210000000",
            "ZeroG Preset": "040200004000",
            "TV Position": "040200003000",
            "Quiet Sleep": "040200008000",
            "Memory 1": "040200001000",
            "Memory 2": "040200002000",
            "Underlight": "040200020000",
            "Lift Head": "040200000001",
            "Lower Head": "040200000002",
            "Lift Foot": "040200000004",
            "Lower Foot": "040200000008",
            # Note: Wave cycles "On High", "On Medium", "On Low", "Off"
            "Wave Massage Cycle": "040280000000",
            # Note: Head and Foot cycles "On Low, "On Medium", "On High", "Off"
            "Head Massage Cycle": "040200000800",
            "Foot Massage Cycle": "040200400000",
            "Massage Off": "040202000000",
            "Keepalive NOOP": "040200000000",
        }
        # Initialise the adapter and connect to the bed before we start waiting for messages.
        self.connectBed(ble)
        # Start the background polling/keepalive/heartbeat function.
        thread = threading.Thread(target=self.bluetoothPoller, args=())
        thread.daemon = True
        thread.start()

    # There seem to be a lot of conditions that cause the bed to disconnect Bluetooth.
    # Here we use the value of 040200000000, which seems to be a noop.
    # This lets us poll the bed, detect a disconnection and reconnect before the user notices.
    def bluetoothPoller(self):
        while True:
            if self.charWriteInProgress is False:
                try:
                    cmd = self.commands.get("Keepalive NOOP", None)
                    self.device.writeCharacteristic(
                        0x0013, bytes.fromhex(cmd), withResponse=True
                    )
                    self.logger.debug("Keepalive success!")
                except Exception:
                    self.logger.error("Keepalive failed! (1/2)")
                    try:
                        # We perform a second keepalive check 0.5 seconds later before reconnecting.
                        time.sleep(0.5)
                        cmd = self.commands.get("Keepalive NOOP", None)
                        self.device.writeCharacteristic(
                            0x0013, bytes.fromhex(cmd), withResponse=True
                        )
                        self.logger.info("Keepalive success!")
                    except Exception:
                        # If both keepalives failed, we reconnect.
                        self.logger.error("Keepalive failed! (2/2)")
                        self.connectBed(ble)
            else:
                # To minimise any chance of contention, we don't heartbeat if a charWrite is in progress.
                self.logger.debug("charWrite in progress, heartbeat skipped.")
            time.sleep(10)

    # Separate out the bed connection to an infinite loop that can be called on init (or a communications failure).
    def connectBed(self, ble):
        while True:
            try:
                self.logger.debug("Attempting to connect to bed.")
                self.device = ble.Peripheral(deviceAddr=self.addr, addrType="random")
                self.logger.info("Connected to bed.")
                self.logger.debug("Enabling bed control.")
                self.device.readCharacteristic(0x001E)
                self.device.readCharacteristic(0x0020)
                self.logger.info("Bed control enabled.")
                return
            except Exception:
                pass
            self.logger.error("Error connecting to bed, retrying in one second.")
            time.sleep(1)

    # Separate out the command handling.
    def send_command(self, name):
        cmd = self.commands.get(name, None)
        if cmd is None:
            # print, but otherwise ignore Unknown Commands.
            self.logger.error(f"Unknown Command '{cmd}' -- ignoring.")
            return
        self.charWriteInProgress = True
        try:
            self.charWrite(cmd)
        except Exception:
            self.logger.error("Error sending command, attempting reconnect.")
            start = time.time()
            self.connectBed(ble)
            end = time.time()
            if (end - start) < 5:
                try:
                    self.charWrite(self, cmd)
                except Exception:
                    self.logger.error(
                        "Command failed to transmit despite second attempt, dropping command."
                    )
            else:
                self.logger.error(
                    "Bluetooth reconnect took more than five seconds, dropping command."
                )
        self.charWriteInProgress = False

    # Separate charWrite function.
    def charWrite(self, cmd):
        self.logger.debug("Attempting to transmit command.")
        self.device.writeCharacteristic(0x0013, bytes.fromhex(cmd), withResponse=True)
        self.logger.info("Command sent successfully.")
        return
