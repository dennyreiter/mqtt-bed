#!/home/pi/.pyenv/shims/python

import os
import logging
import asyncio
import argparse
import yaml
from contextlib import AsyncExitStack
from asyncio_mqtt import Client, MqttError

from controllers.dewertokin import dewertokinBLEController
from controllers.jiecang import jiecangBLEController
from controllers.serta import sertaBLEController
from controllers.linak import linakBLEController

# Load the YAML config
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file) or {}

# Access the configuration variables set in config.yaml
BED_ADDRESS = config.get('BED_ADDRESS', '00:00:00:00:00:00')
BED_TYPE = config.get('BED_TYPE', 'serta')
MQTT_USERNAME = config.get('MQTT_USERNAME', 'mqttbed')
MQTT_PASSWORD = config.get('MQTT_PASSWORD', 'mqtt-bed')
MQTT_SERVER = config.get('MQTT_SERVER', '127.0.0.1')
MQTT_SERVER_PORT = config.get('MQTT_SERVER_PORT', 1883)
MQTT_TOPIC = config.get('MQTT_TOPIC', 'bed')
MQTT_CHECKIN_TOPIC = config.get('MQTT_CHECKIN_TOPIC', 'checkIn/bed')
MQTT_CHECKIN_PAYLOAD = config.get('MQTT_CHECKIN_PAYLOAD', 'OK')
MQTT_ONLINE_PAYLOAD = config.get('MQTT_ONLINE_PAYLOAD', 'online')
MQTT_SHUTDOWN_PAYLOAD = config.get('MQTT_SHUTDOWN_PAYLOAD', 'shutdown')
MQTT_QOS = config.get('MQTT_QOS', 0)
RECONNECT_INTERVAL = config.get('RECONNECT_INTERVAL', 3)


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

        try:
            # Subscribe to topic(s)
            await client.subscribe(MQTT_TOPIC)

            # let everyone know we are online
            logger.info("Connected to MQTT")
            await client.publish(MQTT_CHECKIN_TOPIC, MQTT_ONLINE_PAYLOAD, qos=1)

            # let everyone know we are still alive
            task = asyncio.create_task(
                check_in(client, MQTT_CHECKIN_TOPIC, MQTT_CHECKIN_PAYLOAD)
            )
            tasks.add(task)

            # Wait for everything to complete (or fail due to, e.g., network
            # errors)
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Disconnecting from MQTT")
            await client.publish(MQTT_CHECKIN_TOPIC, MQTT_SHUTDOWN_PAYLOAD, qos=1)
            await client.close()


async def check_in(client, topic, payload):
    while True:
        logger.debug(f'[topic="{topic}"] Publishing message={payload}')
        await client.publish(topic, payload, qos=1)
        await asyncio.sleep(300)


async def bed_command(ble, messages):
    async for message in messages:
        logger.debug(f'[topic_filter="{MQTT_TOPIC}"] {message.payload.decode()}')
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

    if BED_TYPE == "serta":
        ble = sertaBLEController(ble_address)
    elif BED_TYPE == "jiecang":
        ble = jiecangBLEController(ble_address)
    elif BED_TYPE == "dewertokin":
        ble = dewertokinBLEController(ble_address)
    elif BED_TYPE == "linak":
        ble = linakBLEController(ble_address)
    else:
        raise Exception("Unrecognised bed type: " + str(BED_TYPE))

    # Run the bed_loop indefinitely. Reconnect automatically if the connection is lost.
    while True:
        try:
            await bed_loop(ble)
        except MqttError as error:
            logger.error(f'Error "{error}". Reconnecting in {RECONNECT_INTERVAL} seconds.')
        finally:
            await asyncio.sleep(RECONNECT_INTERVAL)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='BLE adjustable bed control over MQTT')
    parser.add_argument('--log', dest='log_level', default='INFO',
                        help='Set the log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')

    args = parser.parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s',
                        datefmt='%H:%M:%S')
    logger = logging.getLogger(__name__)

    # Run the main program
    asyncio.run(main())
