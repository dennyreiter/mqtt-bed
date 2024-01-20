import argparse
import asyncio
import json
import logging
from contextlib import AsyncExitStack

import yaml
from asyncio_mqtt import Client, MqttError

from controllers.dewertokin import dewertokinBLEController
from controllers.jiecang import jiecangBLEController
from controllers.linak import linakBLEController
from controllers.serta import sertaBLEController

# Load the YAML config
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file) or {}

# DO NOT CHANGE VALUES HERE, CHANGE THEM IN config.yaml
# Bed Settings ------------------------------------------------------------------
BED_ADDRESS = config.get("BED_ADDRESS", "00:00:00:00:00:00")
BED_TYPE = config.get("BED_TYPE", "serta")
# MQTT Authorization ------------------------------------------------------------
MQTT_USERNAME = config.get("MQTT_USERNAME", "mqttbed")
MQTT_PASSWORD = config.get("MQTT_PASSWORD", "mqtt-bed")
MQTT_SERVER = config.get("MQTT_SERVER", "127.0.0.1")
MQTT_SERVER_PORT = config.get("MQTT_SERVER_PORT", 1883)
# MQTT Topics & Payloads --------------------------------------------------------
MQTT_BASE_TOPIC = config.get("MQTT_BASE_TOPIC", "bed")
MQTT_AVAILABILITY_TOPIC = config.get("MQTT_AVAILABILITY_TOPIC", "availability")
MQTT_AVAILABLE_PAYLOAD = config.get("MQTT_AVAILABLE_PAYLOAD", "online")
MQTT_NOT_AVAILABLE_PAYLOAD = config.get("MQTT_NOT_AVAILABLE_PAYLOAD", "offline")
MQTT_QOS = config.get("MQTT_QOS", 0)
RECONNECT_INTERVAL = config.get("RECONNECT_INTERVAL", 3)
# Auto Discovery ----------------------------------------------------------------
MQTT_DISCOVERY = config.get("MQTT_DISCOVERY", True)
MQTT_BED_NAME = config.get("MQTT_BED_NAME", "Smart Bed")
MQTT_DISCOVERY_PREFIX = config.get("MQTT_DISCOVERY_PREFIX", "homeassistant")

# Global variable to signal shutdown
shutdown_signal = asyncio.Event()


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
        manager = client.filtered_messages(MQTT_BASE_TOPIC)
        messages = await stack.enter_async_context(manager)
        task = asyncio.create_task(bed_command(ble, messages, client))
        tasks.add(task)

        try:
            # Subscribe to topic(s)
            await client.subscribe(MQTT_BASE_TOPIC)

            # Send HA MQTT Dicovery Topic message
            if MQTT_DISCOVERY:
                await publish_discovery_messages(ble, client)
                await zero_sensors(ble, client)

            # Start sending out hearbeats on the availability topic
            logger.info("Connected to MQTT")
            tasks.add(
                asyncio.create_task(
                    check_in(client, MQTT_AVAILABILITY_TOPIC, MQTT_AVAILABLE_PAYLOAD)
                )
            )

            # Wait for everything to complete (or fail due to, e.g., network errors)
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.debug("Shutdown signal received, closing MQTT connection")
            logger.info("Disconnecting from MQTT")
            await client.publish(
                MQTT_AVAILABILITY_TOPIC, MQTT_NOT_AVAILABLE_PAYLOAD, qos=1
            )
            raise


async def check_in(client, topic, payload):
    while True:
        logger.debug(f"[{MQTT_BASE_TOPIC}/{topic}] {payload}")
        await client.publish(topic, payload, qos=1)
        await asyncio.sleep(300)


async def bed_command(ble, messages, client):
    async for message in messages:
        command = message.payload.decode()
        logger.debug(f"[{MQTT_BASE_TOPIC}] {command}")

        # Send the command, and allow the controller to return a dictionary
        # of states to be returned over MQTT
        state = ble.send_command(message.payload.decode())

        # Publish each state key-value pair to MQTT
        if state:
            for key, value in state.items():
                logger.debug(f"Returned state: {value} publishing to bed/{key}/state")
                await client.publish(f"bed/{key}/state", str(value), qos=1)


async def cancel_tasks(tasks):
    for task in tasks:
        if task.done():
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_discovery_payload(ble, entity, entity_type):
    unique_id = f"{BED_TYPE}_bed_{entity[0].replace(' ', '_')}"
    base_payload = {
        "unique_id": unique_id,
        "name": entity[1],
        "device": {
            "identifiers": [f"{BED_TYPE}_bed"],
            "name": MQTT_BED_NAME,
            "manufacturer": ble.manufacturer,
            "model": ble.model,
            "sw_version": "1.0.0",
        },
    }

    match entity_type:
        case "button":
            base_payload.update(
                {"command_topic": f"{MQTT_BASE_TOPIC}", "payload_press": entity[0]}
            )
        case "switch":
            base_payload.update(
                {
                    "command_topic": f"{MQTT_BASE_TOPIC}/{entity[0]}/toggle",
                    "state_topic": f"{MQTT_BASE_TOPIC}/{entity[0]}/state",
                    "payload": f"{entity[0]}",
                }
            )
        case "sensor":
            base_payload.update(
                {
                    "name": entity[2],
                    "state_topic": f"{MQTT_BASE_TOPIC}/{entity[0]}/state",
                    "unit_of_measurement": entity[1],
                }
            )

    return json.dumps(base_payload)


async def publish_discovery_messages(ble, client):
    entity_types = {
        "button": getattr(ble, "buttons", []),
        "switch": getattr(ble, "switches", []),
        "sensor": getattr(ble, "sensors", []),
    }

    for entity_type, entities in entity_types.items():
        logger.debug(f"{entity_type.capitalize()} Discovery Payloads {'-'*80}")
        for entity in entities:
            topic = f"{MQTT_DISCOVERY_PREFIX}/{entity_type}/{BED_TYPE}_bed/{entity[0]}/config"
            payload = create_discovery_payload(ble, entity, entity_type)
            logger.debug(f"{topic} -- {payload}")
            await client.publish(topic, payload, qos=1, retain=True)


async def zero_sensors(ble, client):
    if hasattr(ble, "sensors"):
        for sensor in ble.sensors:
            state_topic = f"{MQTT_BASE_TOPIC}/{sensor[0]}/state"
            initial_value = "0"
            await client.publish(state_topic, initial_value, qos=1, retain=True)


async def main():
    if BED_TYPE == "serta":
        ble = sertaBLEController(BED_ADDRESS)
    elif BED_TYPE == "jiecang":
        ble = jiecangBLEController(BED_ADDRESS)
    elif BED_TYPE == "dewertokin":
        ble = dewertokinBLEController(BED_ADDRESS)
    elif BED_TYPE == "linak":
        ble = linakBLEController(BED_ADDRESS)
    else:
        raise Exception("Unrecognised bed type: " + str(BED_TYPE))

    # Run the bed_loop indefinitely. Reconnect automatically if the connection is lost.
    try:
        while not shutdown_signal.is_set():
            try:
                await bed_loop(ble)
            except MqttError as error:
                logger.error(
                    f'Error "{error}". Reconnecting in {RECONNECT_INTERVAL} seconds.'
                )
            finally:
                await asyncio.sleep(RECONNECT_INTERVAL)
    except KeyboardInterrupt:
        logger.debug("Ctrl-C caught, setting shutdown signal")
        shutdown_signal.set()

        # Cancel all running tasks gracefully
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]

        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BLE adjustable bed control over MQTT")
    parser.add_argument(
        "--log",
        dest="log_level",
        default="INFO",
        help="Set the log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    args = parser.parse_args()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    # Run the main program
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
