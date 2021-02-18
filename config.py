# mqtt-bed config

BED_ADDRESS = "7C:EC:79:FF:6D:02"

MQTT_USERNAME = "mqttbed"
MQTT_PASSWORD = "mqtt-bed"
MQTT_SERVER = "lenny.homestead.kewanee.net"
# MQTT_SERVER = "192.168.0.77"
MQTT_SERVER_PORT = 1883
MQTT_TOPIC = "bed"

# Don't worry about these unless you want to
MQTT_CHECKIN_TOPIC = "checkIn/bed"
MQTT_CHECKIN_PAYLOAD = "OK"
MQTT_ONLINE_PAYLOAD = "online"
MQTT_QOS = 0

# Extra debug messages
DEBUG = 1
