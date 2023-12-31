#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import bluepy.btle as ble
import logging
import time


class linakBLEController:
    def __init__(self, addr):
        self.logger = logging.getLogger(__name__)
        self.charWriteInProgress = False
        self.addr = addr
        self.uuid = '99FA0002-338A-1024-8A49-009C0215F78A'
        self.commands = {
            "Head Up": "0B00",
            "Head Down": "0A00",
            "Feet Up": "0900",
            "Feet Down": "0800",
            "Both Up": "0100",
            "Both Down": "0000",
            "Light": "9400",
        }
        self.connectBed(ble)

    def print_characteristics(self):
        try:
            for service in self.device.getServices():
                for chara in service.getCharacteristics():
                    self.logger.debug("Characteristic UUID: %s" % chara.uuid)
                    self.logger.debug("Handle: 0x%04x" % chara.getHandle())
                    properties = chara.propertiesToString()
                    self.logger.debug("Properties: %s" % properties)
                    self.logger.debug("----------------------------------------------------------")
        except Exception as e:
            self.logger.error("Error accessing characteristic: %s" % str(e))

    # Separate out the bed connection to an infinite loop that can
    # be called on init (or a communications failure).
    def connectBed(self, ble):
        while True:
            try:
                self.logger.debug("Attempting to connect to bed.")
                self.device = ble.Peripheral(
                    deviceAddr=self.addr,
                    addrType="random"
                )
                self.print_characteristics()
                self.logger.info("Connected to bed.")
                self.logger.debug("Enabling bed control.")
                self.device.readCharacteristic(0x000d)
                self.logger.info("Bed control enabled.")
                return
            except Exception:
                pass
            self.logger.error("Error connecting to bed, retrying in one second.")
            time.sleep(1)

    # Separate charWrite function.
    def charWrite(self, cmd):
        self.logger.debug(f"Attempting to transmit command bytes: {cmd}")
        try:
            self.device.writeCharacteristic(
                0x000e,
                bytes.fromhex(cmd),
                withResponse=False,
            )
        except Exception as e:
            self.logger.error(str(e))
        self.logger.debug("Command sent successfully.")
        return

    def sendCommand(self, name):
        cmd = self.commands.get(name, None)
        if cmd is None:
            # print, but otherwise ignore Unknown Commands.
            self.logger.warning("Received unknown command... ignoring.")
            return
        self.charWriteInProgress = True
        try:
            self.charWrite(cmd)
        except Exception as e:
            self.logger.error("Error sending command, attempting reconnect.")
            start = time.time()
            self.connectBed(ble)
            end = time.time()
            if (end - start) < 5:
                try:
                    self.charWrite(self, cmd)
                except Exception:
                    self.logger.error("Command failed to transmit despite second attempt, dropping command.")
            else:
                self.logger.warning("Bluetooth reconnect took more than five seconds, dropping command.")
        self.charWriteInProgress = False
