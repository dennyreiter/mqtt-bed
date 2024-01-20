#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import time

import bluepy.btle as ble


class linakBLEController:
    def __init__(self, addr):
        self.logger = logging.getLogger(__name__)
        self.write_in_progress = False
        self.addr = addr
        self.uuid = "99FA0002-338A-1024-8A49-009C0215F78A"
        self.commands = {
            "head_up": "0B00",
            "head_down": "0A00",
            "feet_up": "0900",
            "feet_down": "0800",
            "both_up": "0100",
            "both_down": "0000",
            "light": "9400",
        }  # A map of the MQTT payload string to BLE payload bytes
        self.head_increment = 100 / 85  # Number of commands required
        self.feet_increment = 100 / 60  # to go from 0% to 100%

        # To keep track of "state" since the bed doesn't
        self.head_position = 0
        self.feet_position = 0
        self.light_status = False

        # Required fields for MQTT Discovery
        self.manufacturer = "Linak"
        self.model = "KA20IC"
        self.buttons = [
            ("head_up", "Head Up"),
            ("head_down", "Head Down"),
            ("feet_up", "Feet Up"),
            ("feet_down", "Feet Down"),
            ("both_up", "Both Up"),
            ("both_down", "Both Down"),
        ]  # List of Tuples containing the MQTT payloads that should be registered to HA as buttons, and a human-friendly name

        self.switches = [
            ("light", "Bed Light")
        ]  # List of Tuples containing the MQTT payloads for the switch and a friendly name

        self.sensors = [
            ("head_position", "%", "Head Position"),
            ("foot_position", "%", "Feet Position"),
        ]  # List of Tuples containing the MQTT topic for any sensors, the HA unit of measurement, and friendly name

        self._connect_bed(ble)

    # Separate out the bed connection to an infinite loop that can
    # be called on init (or a communications failure).
    def _connect_bed(self, ble):
        while True:
            try:
                self.logger.info("Attempting to connect to bed.")
                self.device = ble.Peripheral(deviceAddr=self.addr, addrType="random")
                self._print_characteristics()
                self.logger.info("Connected to bed.")
                self.logger.debug("Enabling bed control.")
                self.device.readCharacteristic(0x000D)
                self.logger.info("Bed control enabled.")
                return
            except Exception:
                pass
            self.logger.error("Error connecting to bed, retrying in one second.")
            time.sleep(1)

    # Helper function to write command hex to BLE
    def _write_char(self, cmd):
        self.logger.debug(f"Attempting to transmit command bytes: {cmd}")
        try:
            self.device.writeCharacteristic(
                0x000E,
                bytes.fromhex(cmd),
                withResponse=False,
            )
        except Exception as e:
            self.logger.error(str(e))
        self.logger.debug("Command sent successfully.")
        return

    # Public function called by mqtt-bed.py when a command need to be sent over BLE
    def send_command(self, name):
        cmd = self.commands.get(name, None)
        if cmd is None:
            self.logger.warning("Received unknown command... ignoring.")
            return {}

        self.write_in_progress = True
        try:
            self._write_char(cmd)
            return self.update_state_based_on_command(name)
        except Exception:
            self.logger.error("Error sending command, attempting reconnect.")
            start = time.time()
            self._connect_bed(ble)
            end = time.time()
            if (end - start) < 5:
                try:
                    self._write_char(self, cmd)
                except Exception:
                    self.logger.error(
                        "Command failed to transmit despite second attempt, dropping command."
                    )
            else:
                self.logger.warning(
                    "Bluetooth reconnect took more than five seconds, dropping command."
                )
        finally:
            self.write_in_progress = False

    def toggle_light(self):
        self.light_state = not self.light_state
        self.send_command("Light")
        return self.light_state

    def update_state_based_on_command(self, command):
        state = {}
        match command:
            case "head_up":
                self.head_position = min(100, self.head_position + self.head_increment)
                state["head_position"] = round(self.head_position, 2)
            case "head_down":
                self.head_position = max(0, self.head_position - self.head_increment)
                state["head_position"] = round(self.head_position, 2)
            case "feet_up":
                self.feet_position = min(100, self.feet_position + self.feet_increment)
                state["foot_position"] = round(self.head_position, 2)
            case "feet_down":
                self.feet_position = max(0, self.feet_position - self.feet_increment)
                state["feet_position"] = round(self.head_position, 2)
            case "both_down":
                self.head_position = max(0, self.head_position - self.head_increment)
                self.feet_position = max(0, self.feet_position - self.feet_increment)
                state["head_position"] = round(self.head_position, 2)
                state["feet_position"] = round(self.head_position, 2)
            case "both_up":
                self.head_position = min(100, self.head_position + self.head_increment)
                self.feet_position = min(100, self.feet_position + self.feet_increment)
                state["head_position"] = round(self.head_position, 2)
                state["feet_position"] = round(self.head_position, 2)
            case "light":
                self.light_state = not self.light_state
                state["light"] = "ON" if self.light_state else "OFF"

        return state

    def _print_characteristics(self):
        try:
            for service in self.device.getServices():
                for chara in service.getCharacteristics():
                    self.logger.debug("Characteristic UUID: %s" % chara.uuid)
                    self.logger.debug("Handle: 0x%04x" % chara.getHandle())
                    properties = chara.propertiesToString()
                    self.logger.debug("Properties: %s" % properties)
                    self.logger.debug(f"{'-'*58}")
        except Exception as e:
            self.logger.error("Error accessing characteristic: %s" % str(e))
