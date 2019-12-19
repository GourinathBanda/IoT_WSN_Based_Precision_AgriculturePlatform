#include <Arduino.h>
#include <painlessMesh.h>

#include <ESP8266WiFi.h>
#include <OneWire.h>
#include <DallasTemperature.h>

/**
 * @brief The node ID given to the node
 * Keep it unique for each node
 * Change this before flashing
 */
#define NODE_ID "espmesh-00"

// GPIO where the DS18B20 data pin is connected
const int oneWireBus = 4;

// Setup a oneWire instance to communicate with any OneWire devices
OneWire oneWire(oneWireBus);
// Pass our oneWire reference to Dallas Temperature sensor
DallasTemperature sensors(&oneWire);

#define LED 2 // GPIO number of connected LED, ON ESP-12 IS GPIO2

#define MESH_SSID "whateverYouLike"
#define MESH_PASSWORD "somethingSneaky"
#define MESH_PORT 5555

//number of seconds between each reading
#define messageDelayTime 10

//number of seconds between each debug message
#define debugFreq 3

//number of seconds before the node goes to sleep
#define sleepFreq 60

//number of micro-seconds the node remains in sleep
#define sleepDuration 60e6

//number used to identify the gateway (keep constant)
#define GATEWAY_ID 696969

//constants
#define TYPE_DEBUG "debug" //Represents debug messages
#define TYPE_ERROR "error" //Represents error messages
#define TYPE_SYSTEM "system" //Represents system messages
#define TYPE_DATA "data" //Represents telemetry messages

// Prototypes
void sendTelemetryPayload();
void receivedCallback(uint32_t from, String &msg);
void newConnectionCallback(uint32_t nodeId);
void changedConnectionCallback();
void nodeTimeAdjustedCallback(int32_t offset);
void delayReceivedCallback(uint32_t from, int32_t delay);

Scheduler userScheduler; //to control your personal task
painlessMesh mesh;

bool calc_delay = false;
SimpleList<uint32_t> nodes;

void sendTelemetryPayload();
void printDebugOutput();
void initSleep();

/**
 * @brief Used to schedule callbacks after a given delay
 * delay() function cannot be used as it will block the mesh functions 
 * 
 */
Task taskSendData(TASK_SECOND *messageDelayTime, TASK_FOREVER, &sendTelemetryPayload);
Task taskDebugOutput(TASK_SECOND *debugFreq, TASK_FOREVER, &printDebugOutput);
Task initiateDeepSleep(TASK_SECOND *sleepFreq, TASK_FOREVER, &initSleep);

//to avoid the first sleep cycle
bool first = true;

/**
 * @brief Initialise painlessMesh node and set up callbacks 
 * 
 */
void setup()
{
  Serial.begin(115200);

  first = true;

  mesh.setDebugMsgTypes(ERROR | DEBUG); // set before init() so that you can see error messages

  mesh.init(MESH_SSID, MESH_PASSWORD, &userScheduler, MESH_PORT);
  mesh.onReceive(&receivedCallback);
  mesh.onNewConnection(&newConnectionCallback);
  mesh.onChangedConnections(&changedConnectionCallback);
  mesh.onNodeTimeAdjusted(&nodeTimeAdjustedCallback);
  mesh.onNodeDelayReceived(&delayReceivedCallback);

  //schedule and enable tasks
  userScheduler.addTask(taskSendData);
  userScheduler.addTask(taskDebugOutput);
  userScheduler.addTask(initiateDeepSleep);
  taskDebugOutput.enable();
  taskSendData.enable();
  initiateDeepSleep.enable();
}

/**
 * @brief Returns the json string with the given payload
 * 
 * @param type: can be TYPE_DATA, TYPE_ERROR, TYPE_SYSTEM, TYPE_DEBUG
 * @param data: the payload to send
 * 
 * @return String 
 */
String make_json(char type[], char data[])
{
  DynamicJsonDocument doc(1024);

  doc["nodeID"] = NODE_ID;
  doc["type"] = type;
  doc["data"] = data;

  String output;
  serializeJson(doc, output);
  Serial.print("Sending: ");
  serializeJson(doc, Serial);
  Serial.println("");

  //escape " character from json 
  String ret;
  for (unsigned int i = 0; i < output.length(); i++)
  {
    if (output[i] == '"')
    {
      ret += "\\\"";
    }
    else
      ret += output[i];
  }
  return ret;
}
String make_json(char type[], JsonObject data)
{
  DynamicJsonDocument doc(1024);

  doc["nodeID"] = NODE_ID;
  doc["type"] = type;
  doc["data"] = data;

  String output;
  serializeJson(doc, output);

  Serial.print("Sending: ");
  serializeJson(doc, Serial);
  Serial.println("");

  //escape " character from json 
  String ret;
  for (unsigned int i = 0; i < output.length(); i++)
  {
    if (output[i] == '"')
    {
      ret += "\\\"";
    }
    else
      ret += output[i];
  }
  return ret;
}

/**
 * @brief Get the readings as a json string payload
 * 
 * @return String 
 */
String get_reading()
{
  //analog value from the moisture sensor (range: 0-1023)
  int mois = analogRead(0);

  //extract moisture value from the analof reading 
  float RH = (750.0 - (float)mois) / 7.50;

  //get temperature reading
  sensors.requestTemperatures();
  float temperatureC = sensors.getTempCByIndex(0);

  //create json payload
  DynamicJsonDocument doc(1024);
  doc["temperature"] = temperatureC;
  doc["moisture"] = RH;
  JsonObject data = doc.as<JsonObject>();

  return make_json(TYPE_DATA, data);
}

/**
 * @brief notifies the gateway to authenticate this node  
 * 
 */
void setupCloud()
{
  mesh.sendSingle(GATEWAY_ID, make_json(TYPE_SYSTEM, "init"));
}

/**
 * @brief main repeating loop
 * 
 */
void loop()
{
  mesh.update();
}

/**
 * @brief Sends the telemetry payload to the gateway with the sensor readings.
 * 
 */
void sendTelemetryPayload()
{
  mesh.sendSingle(GATEWAY_ID, get_reading());
  taskSendData.setInterval(TASK_SECOND * messageDelayTime);
}

/**
 * @brief Callback for when a message is received 
 * 
 * @param from: node_id of the sender
 * @param msg: message received
 */
void receivedCallback(uint32_t from, String &msg)
{
  
  Serial.printf("Received from %u msg=%s\n", from, msg.c_str());

  //authenticate if the gateway has connected to the mesh
  if (msg.compareTo("gatewayConnected") == 0)
  {
    Serial.printf("%s: Gateway connected to %d", NODE_ID, from);
    setupCloud();
  }
}

/**
 * @brief Callback for when a new node connects to this node
 * 
 * @param nodeId: node id of the connected device
 */
void newConnectionCallback(uint32_t nodeId)
{
  if (nodeId == GATEWAY_ID)
  {
    setupCloud();
    mesh.sendBroadcast("gatewayConnected");
  }
  Serial.printf("New Connection, nodeId = %u\n", nodeId);
  Serial.printf("New Connection, %s\n", mesh.subConnectionJson(true).c_str());
}

/**
/**
 * @brief Callback for when the mesh connections are changed
 * 
 */
void changedConnectionCallback()
{
  Serial.printf("Changed connections\n");

  //prints the connection list 
  nodes = mesh.getNodeList();

  Serial.printf("Num nodes: %d\n", nodes.size());
  Serial.printf("Connection list:");

  SimpleList<uint32_t>::iterator node = nodes.begin();
  while (node != nodes.end())
  {
    Serial.printf(" %u", *node);
    node++;
  }
  Serial.println();
  calc_delay = true;
}

/**
 * @brief Callback for when the node time is adjusted
 * 
 * @param offset
 */
void nodeTimeAdjustedCallback(int32_t offset)
{
  Serial.printf("Adjusted time %u. Offset = %d\n", mesh.getNodeTime(), offset);
}

/**
 * @brief Callback for when the delay is measured between nodes
 * 
 * @param from: node_id of the first node
 * @param delay: delay in micro-seconds
 */
void delayReceivedCallback(uint32_t from, int32_t delay)
{
  Serial.printf("Delay to node %u is %d us\n", from, delay);
}

/**
 * @brief prints debug output
 * 
 */
void printDebugOutput()
{
  Serial.printf("Tick - Time:%u ID:0 Mesh Size: %d\n", mesh.getNodeTime(), nodes.size() + 1);
}

/**
 * @brief function that initiates DeepSleep
 * 
 */
void initSleep()
{
  // Todo: Do any necessary housekeeping
  if (first)
  {
    first = false;
    return;
  }
  Serial.println("Going to sleep");
  mesh.stop();
  ESP.deepSleep(sleepDuration);
}