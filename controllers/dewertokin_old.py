from .dewertokin import dewertokinBLEController
import logging
import threading
import time

import bluepy.btle as ble


class dewertokinOldBLEController(dewertokinBLEController):
    def __init__(self, addr):
        self.logger = logging.getLogger(__name__)
        self.charWriteInProgress = False
        self.addr = addr
        self.manufacturer = "DerwentOkin"
        self.model = "HankookGallery"
        self.commands = {
            "Flat Preset": "E5FE 1601 0000 0203",
            "ZeroG Preset": "E5FE 1601 0000 0104",
            "Memory 1": "E5FE 1601 0000 08FD",
            "Memory 2": "E5FE 1601 0000 09FC",
        }
        # Initialise the adapter and connect to the bed before we start waiting for messages.
        self.connectBed(ble)


    # Separate out the bed connection to an infinite loop that can be called on init (or a communications failure).
    def connectBed(self, ble):
        while True:
            try:
                self.logger.debug("Attempting to connect to bed.")
                # self.device = ble.Peripheral(deviceAddr=self.addr, addrType="random")
                self.device = ble.Peripheral(deviceAddr=self.addr, addrType='public', iface = 0)
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