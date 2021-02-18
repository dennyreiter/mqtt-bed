#!/home/pi/.pyenv/shims/python

import os
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from asyncio_mqtt import Client, MqttError
from gattlib import GATTRequester

# mqtt-bed default config values. Set these in config.py yourself.
BED_ADDRESS = "7C:EC:79:FF:6D:02"
MQTT_USERNAME = "mqttbed"
MQTT_PASSWORD = "mqtt-bed"
MQTT_SERVER = "127.0.0.1"
MQTT_SERVER_PORT = 1883
MQTT_TOPIC = "bed"
MQTT_CHECKIN_TOPIC = "checkIn/bed"
MQTT_CHECKIN_PAYLOAD = "OK"
MQTT_ONLINE_PAYLOAD = "online"
MQTT_QOS = 0
DEBUG = 0

from config import *


class Requester(GATTRequester):
    def on_notification(self, handle, data):
        return


class sertaBLEController:
    def __init__(self, addr, pretend=False):
        self.pretend = pretend
        self.addr = addr
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
        self.req = Requester(addr)
        if DEBUG:
            print("Initialized control for %s" % addr)

    def sendCommand(self, name):
        if not self.req.is_connected():
            self.req.connect(True)
        cmd = self.commands.get(name, None)
        if DEBUG:
            print("Readying command: %s" % str(cmd))
        if cmd is None:
            raise Exception("Command not found: " + str(name))
        if DEBUG:
            print(bytearray.fromhex(cmd))

        if DEBUG:
            print("Sending BLE command: %s" % cmd)
        if self.pretend:
            (" ".join(cmd_args))
            res = 0
        else:
            res = self.req.write_by_handle(0x0020, bytes.fromhex(cmd))
        if DEBUG:
            print("BLE command sent")
            print(res)
        return res


async def bed_loop(ble):
    async with AsyncExitStack() as stack:
        # Keep track of the asyncio tasks that we create, so that
        # we can cancel them on exit
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)

        # Connect to the MQTT broker
        client = Client(
            MQTT_SERVER,
            port=MQTT_SERVER_PORT,
            username=MQTT_USERNAME,
            password=MQTT_PASSWORD,
        )
        await stack.enter_async_context(client)

        # Set up the topic filter
        manager = client.filtered_messages(MQTT_TOPIC)
        messages = await stack.enter_async_context(manager)
        task = asyncio.create_task(bed_command(ble, messages))
        tasks.add(task)

        # Subscribe to topic(s)
        await client.subscribe(MQTT_TOPIC)

        # let everyone know we are online
        if DEBUG:
            print("Going online")
        await client.publish(MQTT_CHECKIN_TOPIC, MQTT_ONLINE_PAYLOAD, qos=1)

        # let everyone know we are still alive
        task = asyncio.create_task(
            check_in(client, MQTT_CHECKIN_TOPIC, MQTT_CHECKIN_PAYLOAD)
        )
        tasks.add(task)

        # Wait for everything to complete (or fail due to, e.g., network
        # errors)
        await asyncio.gather(*tasks)


async def check_in(client, topic, payload):
    while True:
        if DEBUG:
            print(f'[topic="{topic}"] Publishing message={payload}')
        await client.publish(topic, payload, qos=1)
        await asyncio.sleep(30)


async def bed_command(ble, messages):
    async for message in messages:
        template = f'[topic_filter="{MQTT_TOPIC}"] {{}}'
        if DEBUG:
            print(template.format(message.payload.decode()))
        ble.sendCommand(message.payload.decode())


async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def main():

    ble_address = os.environ.get("BLE_ADDRESS", BED_ADDRESS)

    if ble_address is None:
        raise Exception("BLE_ADDRESS env not set")

    ble = sertaBLEController(ble_address)

    # Run the bed_loop indefinitely. Reconnect automatically
    # if the connection is lost.
    reconnect_interval = 3  # [seconds]
    while True:
        try:
            await bed_loop(ble)
        except MqttError as error:
            print(f'Error "{error}". Reconnecting in {reconnect_interval} seconds.')
        finally:
            await asyncio.sleep(reconnect_interval)


asyncio.run(main())
