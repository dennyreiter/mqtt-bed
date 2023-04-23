#!/usr/bin/python3

import asyncio
import yaml
from contextlib import AsyncExitStack
from asyncio_mqtt import Client, MqttError

from controllers.dewertokin import dewertokinBLEController
from controllers.jiecang import jiecangBLEController
from controllers.serta import sertaBLEController

MQTT_QOS = 0
DEBUG = 0


class Bed:
    def __init__(self, raw):
        self.type = raw["type"]
        self.address = raw["address"]


class Mqtt:
    def __init__(self, raw):
        self.username = raw["username"]
        self.password = raw["password"]
        self.server = raw["server"]
        self.serverPort = raw["server_port"]
        self.topic = raw["topic"]
        self.checkin = raw["checkin"]
        self.online = raw["online"]
        self.qos = raw["qos"]


class Config:
    def __init__(self, raw):
        self.bed = Bed(raw["bed"])
        self.mqtt = Mqtt(raw["mqtt"])


with open("config.yaml", "r") as file:
    config = Config(yaml.safe_load(file))


async def bed_loop(ble):
    async with AsyncExitStack() as stack:
        # Keep track of the asyncio tasks that we create, so that
        # we can cancel them on exit
        tasks = set()
        stack.push_async_callback(cancel_tasks, tasks)

        # Connect to the MQTT broker
        client = Client(
            config.mqtt.server,
            port=config.mqtt.serverPort,
            username=config.mqtt.username,
            password=config.mqtt.password,
        )
        await stack.enter_async_context(client)

        # Set up the topic filter
        manager = client.filtered_messages(config.mqtt.topic)
        messages = await stack.enter_async_context(manager)
        task = asyncio.create_task(bed_command(ble, messages))
        tasks.add(task)

        # Subscribe to topic(s)
        await client.subscribe(config.mqtt.topic)

        # let everyone know we are online
        if DEBUG:
            print("Going online")
        await client.publish(
            config.mqtt.checkin["topic"], config.mqtt.online["payload"], qos=1
        )

        # let everyone know we are still alive
        task = asyncio.create_task(
            check_in(
                client, config.mqtt.checkin["topic"], config.mqtt.checkin["payload"]
            )
        )
        tasks.add(task)

        # Wait for everything to complete (or fail due to, e.g., network errors)
        await asyncio.gather(*tasks)


async def check_in(client, topic, payload):
    while True:
        if DEBUG:
            print(f'[topic="{topic}"] Publishing message={payload}')
        await client.publish(topic, payload, qos=1)
        await asyncio.sleep(300)


async def bed_command(ble, messages):
    async for message in messages:
        if DEBUG:
            template = f'[topic_filter="{config.mqtt.topic}"] {{}}'
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
    ble_address = config.bed.address

    if ble_address is None:
        raise Exception("Bed Address not set")

    if config.bed.type == "serta":
        ble = sertaBLEController(ble_address)
    elif config.bed.type == "jiecang":
        ble = jiecangBLEController(ble_address)
    elif config.bed.type == "dewertokin":
        ble = dewertokinBLEController(ble_address)
    else:
        raise Exception("Unrecognised bed type: " + str(config.bed.type))

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
