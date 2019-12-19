# region imports

import argparse
import datetime
import json
import os
import socket
import ssl
import time
from time import ctime
from time import sleep
import pytz
import sys

import logging

# persistance
import pickle

# mqtt
import jwt
import paho.mqtt.client as mqtt

# for running shell commands
import platform
import subprocess
import shlex

# for big query
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# import variables and constants
from dfpl_gateway import *

# endregion

# defines the print output verbosity
READING_LEVEL = 5

# class instances
logger = {}
process = {}


# cloud setup variables
# change these according to your cloud setup
class SetupVariables:
    project_id = 'dfpl-project-001'
    cloud_region = 'asia-east1'
    registry_id = 'dfpl-temp'
    gateway_id = 'test-gateway'
    algorithm = 'RS256'
    mqtt_bridge_hostname = 'mqtt.googleapis.com'
    mqtt_bridge_port = 8883
    jwt_expires_minutes = 1200
    path_to_bqcreds = ''


setupVars = SetupVariables()

# stores all information related to the gateway's current state
class GatewayState:
    # This is the topic that the device will receive configuration updates on.
    mqtt_config_topic = ''

    # This is the configuration, updated from cloud.
    # Used to store the variables that define the normal operation of the gateway
    # farmID
    # datasetID
    config = {"farmID": "farm_001", "datasetID": "rawSensorData"}

    # Host the gateway will connect to
    mqtt_bridge_hostname = ''
    mqtt_bridge_port = 8883

    # For all PUBLISH messages which are waiting for PUBACK. The key is 'mid'
    # returned by publish().
    pending_responses = {}

    # For all attach messages which are waiting for PUBACK.
    # Subscriptions are executed after ACK is received
    pending_attach = {}

    # For all SUBSCRIBE messages which are waiting for SUBACK. The key is
    # 'mid'.
    pending_subscribes = {}

    # Numeric nodeId_nums assigned by mesh
    nodeID_num_for = {}

    # for all SUBSCRIPTIONS. The key is subscription topic.
    subscriptions = {}

    # Indicates if MQTT client is connected or not
    connected = False

    def __init__(self):
        try:
            file = open('saved.config', 'rb')
            self.config = pickle.load(file)
            logger.debug('Loaded saved config: {}'.format(self.config))
        except FileNotFoundError:
            logger.warning('Saved config not found')

    def update_config(self, conf):
        self.config = conf
        file = open('saved.config', 'wb')
        pickle.dump(self.config, file)
        file.close()
        logger.debug('Updated config: {}'.format(self.config))


gateway_state = {}

# handles archival storage to the BigQuery database
class BigQueryHandler:

    def __init__(self):
        global setupVars
        global gateway_state

        # Instantiates a client
        self.bigquery_client = bigquery.Client.from_service_account_json(
            setupVars.path_to_bqcreds)

        try:
            self.datasetID = gateway_state.config['datasetID']
        except KeyError:
            self.datasetID = 'rawSensorData'

        self.get_dataset()

    # Prepares a reference to the dataset
    def get_dataset(self):
        self.dataset_ref = self.bigquery_client.dataset(self.datasetID)
        try:
            self.bigquery_client.get_dataset(self.dataset_ref)
        except NotFound:
            # Create Dataset
            dataset = bigquery.Dataset(self.dataset_ref)
            dataset = self.bigquery_client.create_dataset(dataset)
            logger.info('Dataset {} created.'.format(dataset.dataset_id))

    # Prepares a reference to the specific table
    def get_table(self):
        global gateway_state
        farmID = gateway_state.config['farmID']

        # Prepares a reference to the table
        self.table_ref = self.dataset_ref.table(farmID+'_readings')

        # timestamp:TIMESTAMP,nodeID:STRING,temperature:FLOAT,moisture:FLOAT
        # {"temperature": 24.875, "moisture": 7.866667, "timestamp": "11-11-2019, 19:14:57", "nodeID": "espmesh-00"}
        try:
            self.bigquery_client.get_table(self.table_ref)
        except NotFound:
            schema = [
                bigquery.SchemaField(
                    'timestamp', 'TIMESTAMP', mode='REQUIRED'),
                bigquery.SchemaField('nodeID', 'STRING', mode='REQUIRED'),
                bigquery.SchemaField('temperature', 'FLOAT', mode='REQUIRED'),
                bigquery.SchemaField('moisture', 'FLOAT', mode='REQUIRED'),
            ]
            table = bigquery.Table(self.table_ref, schema=schema)
            table = self.bigquery_client.create_table(table)
            logger.warning('table {} created.'.format(table.table_id))

    # streams the telemetry to the BQ table
    def addToBQ(self, data):
        self.get_table()

        table = self.bigquery_client.get_table(self.table_ref)  # API call

        rows_to_insert = [data]
        errors = self.bigquery_client.insert_rows(
            table, rows_to_insert)  # API request
        return errors


bqHandler = {}


# region IoT Core Setup

# Creates a jwt token for authenticating to Google Cloud IoT Core
def create_jwt(project_id, private_key_file, algorithm, jwt_expires_minutes):
    """Creates a JWT (https://jwt.io) to establish an MQTT connection.
            Args:
             project_id: The cloud project ID this device belongs to
             private_key_file: A path to a file containing either an RSA256 or
                             ES256 private key.
             algorithm: Encryption algorithm to use. Either 'RS256' or 'ES256'
             jwt_expires_minutes: The time in minutes before the JWT expires.
            Returns:
                An MQTT generated from the given project_id and private key,
                which expires in 20 minutes. After 20 minutes, your client will
                be disconnected, and a new JWT will have to be generated.
            Raises:
                ValueError: If the private_key_file does not contain a known
                key.
            """

    token = {
        # The time that the token was issued at
        'iat': datetime.datetime.utcnow(),
        # The time the token expires.
        'exp': (
            datetime.datetime.utcnow() +
            datetime.timedelta(minutes=jwt_expires_minutes)),
        # The audience field should always be set to the GCP project id.
        'aud': project_id
    }

    # Read the private key file.
    with open(private_key_file, 'r') as f:
        private_key = f.read()

    logger.info('Creating JWT using {} from private key file {}'.format(
        algorithm, private_key_file))

    return jwt.encode(token, private_key, algorithm=algorithm)

# Creates the MQTT client for Cloud IoT Core


def get_client(
        project_id, cloud_region, registry_id, gateway_id, private_key_file,
        algorithm, ca_certs, mqtt_bridge_hostname, mqtt_bridge_port,
        jwt_expires_minutes):

    # The client_id is a unique string that
    # identifies this device. For Google Cloud IoT Core, it must be in the
    # format below
    client_template = 'projects/{}/locations/{}/registries/{}/devices/{}'
    client_id = client_template.format(
        project_id, cloud_region, registry_id, gateway_id)
    client = mqtt.Client(client_id)

    # With Google Cloud IoT Core, the username field is ignored, and the
    # password field is used to transmit a JWT to authorize the device.
    client.username_pw_set(
        username='unused',
        password=create_jwt(
            project_id, private_key_file, algorithm,
            jwt_expires_minutes))

    # Enable SSL/TLS support.
    client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)

    # Register message callbacks. https://eclipse.org/paho/clients/python/docs/
    # describes additional callbacks that Paho supports.

    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_subscribe = on_subscribe

    # Connect to the Google MQTT bridge.
    client.connect(mqtt_bridge_hostname, mqtt_bridge_port)

    return client

# endregion


# region MQTT Callbacks

# Convert a Paho error to a human readable string.
def error_str(rc):
    return '{}: {}'.format(rc, mqtt.error_string(rc))


# Paho callback for when a device connects.
def on_connect(client, unused_userdata, unused_flags, rc):
    logger.debug('on_connect' + mqtt.connack_string(rc))

    gateway_state.connected = True

    # Subscribe to the config topic.
    client.subscribe(gateway_state.mqtt_config_topic, qos=1)


# Paho callback for when a device disconnects
def on_disconnect(client, unused_userdata, rc):
    logger.info('on_disconnect', error_str(rc))
    gateway_state.connected = False

    # re-connect
    # NOTE: should implement back-off here, but it's a tutorial
    client.connect(
        gateway_state.mqtt_bridge_hostname, gateway_state.mqtt_bridge_port)


# Paho callback when a message is successfully sent to the broker
def on_publish(client, userdata, mid):
    logger.debug('PUBACK received, userdata {}, mid {}'.format(
        userdata, mid))

    try:
        # If a PUBACK for attach is received for a Node, it is subscribed for updates
        client_addr, message = gateway_state.pending_attach.pop(mid)
        logger.info(
            'Device {} is attached. Subscribing it for updates.'.format(client_addr))
        sub_for_updates(client, client_addr)
        logger.debug('Pending attaches count {}'.format(
            len(gateway_state.pending_attach)))

    except KeyError:
        logger.debug('mid: {}. Not a attach ack'.format(mid))
        try:
            client_addr, message = gateway_state.pending_responses.pop(mid)
            sendTo(client_addr, payload.decode("utf-8"))
            logger.debug('Pending response count {}'.format(
                len(gateway_state.pending_responses)))
        except KeyError:
            logger.error('Unable to find mid {}'.format(mid))


# Paho callback for a SUBACK
def on_subscribe(unused_client, unused_userdata, mid, granted_qos):
    logger.info('on_subscribe: mid {}, qos {granted_qos}'.format(mid))
    try:
        client_addr, response = gateway_state.pending_subscribes[mid]
        sendTo(client_addr, response)
    except KeyError:
        logger.warning('Unable to find mid: {}'.format(mid))


# Callback when the device receives a message on a subscription
# Redirects the message according to the subscription list
def on_message(unused_client, unused_userdata, message):

    global gateway_state

    payload = message.payload
    qos = message.qos
    logger.info('Received message \'{}\' on topic \'{}\' with Qos {}'.format(
        payload.decode("utf-8"), message.topic, qos))

    # Configuration topic for the gateway
    if message.topic == gateway_state.mqtt_config_topic:
        handle_config_update(payload)
        return

    # Configuration topics for the attached nodes
    try:
        client_addr = gateway_state.subscriptions[message.topic]
        sendTo(client_addr, payload.decode("utf-8"))
        logger.info('Sent message to device {}'.format(client_addr))
    except KeyError:
        logger.warning('Nobody subscribes to topic {}'.format(message.topic))


# endregion


# region Event Handlers

# subscribes the NodeID to configuration updates and commands
def sub_for_updates(client, nodeID):
    template = '{{ "device": "{}", "command": "{}", "status" : "ok" }}'

    subscribe_topic = '/devices/{}/config'.format(nodeID)
    logger.info('Subscribing to config topic: {}'.format(subscribe_topic))
    _, mid = client.subscribe(subscribe_topic, qos=1)
    response = template.format(nodeID, 'subscribe')
    gateway_state.subscriptions[subscribe_topic] = (nodeID)
    logger.debug('Save mid {} for response {}'.format(mid, response))
    gateway_state.pending_subscribes[mid] = (nodeID, response)

    command_topic = '/devices/{}/commands/#'.format(nodeID)
    logger.info('Subscribing to command topic: {}'.format(command_topic))
    _, mid = client.subscribe(command_topic, qos=0)
    gateway_state.subscriptions[command_topic] = (nodeID)

    # TODO add suport for error logs
    #logger.info('Subscribing to error topic: {}'.format(command_topic))


# handles the configuration updates for the gateway
def handle_config_update(payload):

    if not payload:
        return

    # The config is passed in the payload of the message. In this example,
    # the server sends a serialized JSON string.
    logger.info('Received updated config: {}'.format(payload))
    try:
        config = json.loads(payload, encoding='utf-8')
    except ValueError:  # includes simplejson.decoder.JSONDecodeError
        logger.error('Decoding JSON in config has failed')
        logger.error('Invalid json: {}'.format(output))
        return

    if not config:
        logger.error('Empty config, Json error: {}'.format(output))
        return

    global gateway_state
    gateway_state.update_config(config)


# attaches the device_id to this gateway
# only attached devices can send telemetry to the cloud through this gateway
# the device_id needs to be bound to the gateway before
def attach_device(client, device_id):
    attach_topic = '/devices/{}/attach'.format(device_id)
    logger.info('Attach device:{}, {}'.format(device_id, attach_topic))
    return client.publish(attach_topic, "", qos=1)


# detaches the device_id from this gateway
def detatch_device(client, device_id):
    detach_topic = '/devices/{}/detach'.format(device_id)
    logger.info('Detatch device:{}, {}'.format(device_id, detach_topic))
    return client.publish(detach_topic, "", qos=1)


# handles a system message from a node
def handleSystemMessage(client, nodeID, msg, nodeID_num):
    template = '{{ "device": "{}", "command": "{}", "status" : "ok" }}'

    # auth request from a node
    if msg == 'init':

        gateway_state.nodeID_num_for[nodeID] = nodeID_num

        # detach
        _, detach_mid = detatch_device(client, nodeID)
        response = template.format(nodeID, 'detach')
        logger.debug('Save mid {} for response {}'.format(
            detach_mid, response))
        gateway_state.pending_responses[detach_mid] = (
            nodeID, response)

        # attach
        _, attach_mid = attach_device(client, nodeID)
        response = template.format(nodeID, 'attach')
        logger.debug('Save mid {} for response {}'.format(
            attach_mid, response))
        # Pending Subscribes are queued after the mid is acked by the server
        gateway_state.pending_attach[attach_mid] = (nodeID, response)

        # Needed time for the server to attach device
        # Only then it will accept subscriptions
        # The nodes are attached only when PUBACK is received for the nodeID

        # logger.info("Sleeping for 5...")
        # time.sleep(5)

    else:
        logger.warning('undefined system msg: {}'.format(msg))


# handles a telemetry message form a node
def handleReadings(client, nodeID, reading):

    # Adding timestamp, nodeID and derived variables
    reading['timestamp'] = get_formatted_time()
    reading['nodeID'] = nodeID

    # Publishing to IoT for live access
    template = '{{ "device": "{}", "command": "{}", "status" : "ok" }}'
    logger.debug('Sending telemetry event for device {}'.format(nodeID))

    mqtt_topic = '/devices/{}/events'.format(nodeID)

    logger.info('Publishing message to topic {} with payload \'{}\''.format(
        mqtt_topic, json.dumps(reading)))

    if isinstance(reading, str):
        _, event_mid = client.publish(mqtt_topic, reading, qos=1)
    else:
        _, event_mid = client.publish(mqtt_topic, json.dumps(reading), qos=1)

    response = template.format(nodeID, 'event')
    logger.debug('Save mid {} for response {}'.format(event_mid, response))
    gateway_state.pending_responses[event_mid] = (nodeID, response)

    # Saving to BigQuery for archival storage
    errors = bqHandler.addToBQ(reading)
    if errors != []:
        logger.error("Error adding to BigQuery")
        logger.error(errors)

    # Adding to logs for local backup
    logger.log(READING_LEVEL, reading)


# sends the message to the nodeID in the mesh
def sendTo(nodeID, message):
    # output format:
    # <numeric_nodeID> <message>

    to_send = '{} {}\n'.format(gateway_state.nodeID_num_for[nodeID], message)

    logger.info('Sending {}'.format(to_send))

    # sends the message to the process on which the painlessMeshBoost bridge is running which sends the payload to the specific node_id
    process.stdin.write(to_send.encode('utf-8'))

# endregion


# region helper functions


def initial_setup(args):
    global gateway_state
    global setupVars
    global logger
    global bqHandler
    global process

    setupLogging(args.log)

    logger.debug("Initating setup")

    gateway_state = GatewayState()

    setupVars.gateway_id = args.gateway_id

    # Subscription topic for configuration updates for the gateway
    gateway_state.mqtt_config_topic = '/devices/{}/config'.format(
        setupVars.gateway_id)

    gateway_state.mqtt_bridge_hostname = setupVars.mqtt_bridge_hostname
    gateway_state.mqtt_bridge_port = setupVars.mqtt_bridge_hostname

    setupVars.path_to_bqcreds = args.json_creds

    bqHandler = BigQueryHandler()

    client = get_client(
        setupVars.project_id, setupVars.cloud_region, setupVars.registry_id,
        setupVars.gateway_id, args.private_key_file, setupVars.algorithm,
        args.ca_certs, setupVars.mqtt_bridge_hostname, setupVars.mqtt_bridge_port,
        setupVars.jwt_expires_minutes)

    return client


# parses command line arguments
def parse_command_line_args():
    kdd = keys_dir
    if is_windows():
        kdd = kdd + '\\'
    else:
        kdd = kdd+'/'

    parser = argparse.ArgumentParser(description=(
        'Example Google Cloud IoT Core MQTT device connection code.'))
    parser.add_argument(
        '--gateway_id', required=True, help='Gateway Name/ID')
    parser.add_argument(
        '--private_key_file', default='{}rsa_private.pem'.format(kdd),
        help='Path to private key file.')
    parser.add_argument(
        '--ca_certs', default='{}roots.pem'.format(kdd),
        help=('CA root from https://pki.google.com/roots.pem'))
    parser.add_argument(
        '--json_creds', default='{}bq-manager.json'.format(kdd),
        help=('Path to json creds for a Service Account with r/w access to BigQuery'))
    parser.add_argument(
        '--log',
        choices=('reading', 'all', 'debug', 'info',
                 'warning', 'error', 'critical'),
        default='error',
        help='Console output logging.')
    parser.add_argument(
        '--interface',
        default='wlan0',
        help='Network interface through which the gateway is connected to the mesh')
    return parser.parse_args()


# helper function to get the proper formatted time with timezone to store as timestamp in the BigQuery database
def get_formatted_time(timezone='Asia/Kolkata'):
    tz = datetime.datetime.now(pytz.timezone(timezone)).strftime("%z")
    tz = tz[:3]+':'+tz[3:]
    timestamp = datetime.datetime.now(pytz.timezone(
        'Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S.%f")+tz
    return timestamp


# helper function to set up logging
def setupLogging(cLevel):
    print("setting log level to {}".format(cLevel))
    custom = False
    if cLevel == 'debug':
        cLevel = logging.DEBUG
    elif cLevel == 'info':
        cLevel = logging.INFO
    elif cLevel == 'warning':
        cLevel = logging.WARNING
    elif cLevel == 'error':
        cLevel = logging.ERROR
    elif cLevel == 'critical':
        cLevel = logging.CRITICAL
    elif cLevel == 'all':
        cLevel = READING_LEVEL
    elif cLevel == 'reading':
        cLevel = logging.ERROR
        custom = True

    class LogFilter(object):
        def __init__(self, level, level2=None):
            self.__level = level
            self.__level2 = level2

        def filter(self, logRecord):
            # handler1.addFilter(MyFilter(logging.INFO))
            # handler2.addFilter(MyFilter(logging.ERROR))
            if not self.__level2:
                return logRecord.levelno <= self.__level
            else:
                return logRecord.levelno <= self.__level or logRecord.levelno >= self.__level2

    global logger
    # create logger with 'gatway-root'
    logging.addLevelName(READING_LEVEL, 'Reading')
    logger = logging.getLogger('gatway-root')
    logger.setLevel(READING_LEVEL)

    path = os.getcwd()
    path = path + 'logs'
    try:
        os.mkdir('logs')
    except FileExistsError:
        print("Logs directory already exists")
    except OSError:
        sys.exit("Creation of the directory %s failed" % path)

    # create file handler which logs even debug messages
    fh = logging.FileHandler('./logs/full-logs.log')
    fh.setLevel(logging.DEBUG)

    # create file handler which logs just errors
    eh = logging.FileHandler('./logs/error-log.log')
    eh.setLevel(logging.ERROR)

    # create file handler which logs just readings
    rh = logging.FileHandler('./logs/reading.log')
    rh.setLevel(READING_LEVEL)
    rh.addFilter(LogFilter(READING_LEVEL))

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(cLevel)

    if custom:
        ch2 = logging.StreamHandler()
        ch2.setLevel(READING_LEVEL)
        ch2.addFilter(LogFilter(READING_LEVEL))
        ch2Format = logging.Formatter('%(asctime)s - %(message)s')
        ch2.setFormatter(ch2Format)
        logger.addHandler(ch2)

    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    eh.setFormatter(formatter)
    readingFormat = logging.Formatter('%(asctime)s - Packet: [%(message)s]')
    rh.setFormatter(readingFormat)

    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.addHandler(rh)
    logger.addHandler(eh)


# get wifi ip address
def get_ip_address(args):
    win = is_windows()
    wlan_interface = args.interface

    if win:
        gw = os.popen(
            "netsh interface ip show config name=\"WiFi\" | findstr \"Default Gateway:\"").read().split()
    else:
        gw = os.popen(
            "ip -4 address show dev {} | grep -e \"inet\"".format(wlan_interface)).read().split()

    while(not gw):
        print("Waiting for wifi...")
        sleep(1)
        if win:
            gw = os.popen(
                "netsh interface ip show config name=\"WiFi\" | findstr \"Default Gateway:\"").read().split()
        else:
            gw = os.popen(
                "ip -4 address show dev {} | grep -e \"inet\"".format(wlan_interface)).read().split()

    if win:
        ipaddress = gw[2]
    else:
        ipa = gw[1].split('/')[0].split('.')
        # get gateway ip
        ipaddress = ipa[0]+'.'+ipa[1]+'.'+ipa[2]+'.1'

    return ipaddress


# checks whether the operating system is Windows or not
def is_windows():
    if "Windows" in platform.platform():
        return True
    return False

# endregion


def main():
    global gateway_state
    global logger
    global process

    args = parse_command_line_args()

    client = initial_setup(args)

    ipaddress = get_ip_address(args)

    # runs the painlessMeshBoost bridge as a subprocess with which we can communicate
    # and receive messages from the nodes in the mesh
    command = 'painlessMeshBoost -n 696969 --client '+ipaddress
    if is_windows():
        process = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            shell=True,
            bufsize=0)
    else:
        process = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            bufsize=0)

    while True:
        client.loop()
        if gateway_state.connected is False:
            logger.info('connect status {}'.format(gateway_state.connected))
            time.sleep(1)
            continue

        # command output
        output = process.stdout.readline()

        if output == '' and process.poll() is not None:
            continue

        output = str(output.strip(), encoding='utf-8')
        if output == "" or 'setLogLevel' in output:
            continue

        try:
            logline = json.loads(output)
        except ValueError:  # includes simplejson.decoder.JSONDecodeError
            logger.warning('Decoding JSON has failed')
            logger.error('invalid json: {}'.format(output))
            continue

        if not logline:
            logger.error('invalid json syntax: {}'.format(output))
            continue

        event = logline['event']

        if event == 'change' or event == 'connect' or event == 'offset':
            # debug log
            logger.debug('Mesh Log: [{}]'.format(logline))

        elif event == 'receive':
            # direct message
            TYPE_DEBUG = "debug"
            TYPE_ERROR = "error"
            TYPE_SYSTEM = "system"
            TYPE_DATA = "data"

            datastr = logline['msg']

            # ignore broadcast
            if datastr == 'gatewayConnected':
                continue

            logger.debug('Received message: [{}]'.format(logline))

            try:
                data = json.loads(datastr)
            except ValueError:  # includes simplejson.decoder.JSONDecodeError
                logger.warning('Decoding data JSON has failed')
                logger.error('invalid json: {}'.format(datastr))
                continue

            if not data:
                logger.error('invalid data received: {}'.format(output))
                continue

            ty = data['type']
            nodeID = data['nodeID']
            msg = data['data']
            nodeID_num = logline['nodeId']

            logger.info('Received Data: {} from Node: {}'.format(data, nodeID))

            if ty == TYPE_SYSTEM:
                handleSystemMessage(client, nodeID, msg, nodeID_num)
            elif ty == TYPE_DATA:
                handleReadings(client, nodeID, msg)
            else:
                logger.warning("Unknown message type '{}'".format(ty))
                logger.war
        else:
            logger.warning(
                "Unknown event: {}, details: {}".format(event, logline))

if __name__ == '__main__':
    main()
