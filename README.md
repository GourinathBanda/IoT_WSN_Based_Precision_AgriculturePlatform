# Project-001 Technical Documentation



## Architecture:

The architecture is composed of 3 layers: sensor, gateway, and cloud back-end.
![Network Architecture](../master/documentation/imgs/layers.png?raw=true)

The deployment process requires a Windows 10 (x64) machine to flash the nodes once after which they can be easily reused.

Each node is bound to a gateway which then send the telemetry to the cloud.

## Initial Setup before deployment (needs to be done only once)

1. Setup Cloud(Register Nodes, Register Gateway, Bind nodes to gateway). See [Cloud Setup](../master/documentation/cloud.md)
2. Setup Gateway (modify relevant parameters in the python script). See [Gateway Setup](../master/dfpl-project001-gateway/README.md)
3. Flash each node with the registered NodeIDs. See [Node Setup](../master/meshwdata/README.md)

## Steps to deploy:

1. Turn on the gateway (Raspberry Pi)
   * Connect the given USB C power adapter  to the raspberry pi.
   * Connect the given 4G dongle to raspberry pi via usb
   * Turn on the raspberry pi
2. Place the nodes in the field
3. Turn them on
