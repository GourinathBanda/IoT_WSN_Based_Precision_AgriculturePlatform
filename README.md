# Project-001 Technical Documentation

This repository contains all components that are a part of this solution.

There are 3 main component layers: the nodes, the gateway, and cloud back-end.

![Network Architecture](../master/documentation/imgs/layers.png?raw=true)

* The node: An ES8266 with sensors that sends data to the gateway. Each node has a unique NodeID that is used to configure it on the GCP console.

* The gateway:  A python script running on a raspberry pi that connects to the mesh via wifi and sends the telemetry data to Cloud. The cloud configuration: `{ "farmID" : "farm_001" , "datasetID": "rawSensorData"}` decides the dataset to which the gateway is adding data to and the farmID (which decides the name of the table in the database).

* Cloud: Google IoT Core and BigQuery are used for device management and archival storage respectively.

Each node and gateway only needs to be set up once, after which it can be easily deployed. The initial setup process requires a Windows 10 (x64) machine to flash the nodes.


## Initial Setup before deployment (needs to be done only once)

1. Setup Cloud(Register Gateway, Register Nodes, Bind nodes to gateway). See [Cloud Setup](../master/documentation/cloud.md)
2. Setup Gateway (modify relevant parameters in the python script). See [Gateway Setup](https://github.com/Raghav-intrigue/dfpl-project001-gateway)
3. Flash each node with the registered NodeIDs. See [Node Setup](https://github.com/Raghav-intrigue/dfpl-project001-node)

## Steps to deploy:

1. Turn on the gateway (Raspberry Pi)
   * Connect the given USB C power adapter  to the raspberry pi.
   * Connect the given 4G dongle to raspberry pi via usb
   * Turn on the raspberry pi
2. Place the nodes in the field
3. Turn them on
