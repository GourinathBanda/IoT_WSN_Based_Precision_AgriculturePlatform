# Cloud Setup

[![Open in Cloud Shell][shell_img]][shell_link]

[shell_img]: https://gstatic.com/cloudssh/images/open-btn.png
[shell_link]: https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/Raghav-intrigue/dfpl-project001&page=editor&open_in_editor=documentation/cloud.md


Before following any of the steps below, ensure that these environment variables are set according to your cloud setup.

Run the following commands to set the environment variables (given with the current values) :

```sh
export PROJECT_ID="dfpl-project-001"
export PUBSUB_TOPIC="iotcore-topic"
export PUBSUB_SUBSCRIPTION="iotcore-subscription"
export REGISTRY_NAME="dfpl-temp"
export REGION_NAME="asia-east1"
export GATEWAY_NAME="test-gateway"
```

## Register node

1. Open cloud shell, set the environment variables
2. Set the nodeID you want using `export MDEVICE_NAME="espmesh-00"`
3. Execute:
   
   ```sh
   gcloud iot devices create $MDEVICE_NAME --region=$REGION_NAME  --registry=$REGISTRY_NAME --device-type=non-gateway
   ```

## Bind node to gateway

1. Open cloud shell, set the environment variables
2. Set the nodeID you want using `export MDEVICE_NAME="espmesh-00"`
3. Set the GATEWAY_NAME you want to bind it to using `export GATEWAY_NAME="test-gateway"`
4. Execute:
   
   ```sh
    gcloud iot devices gateways bind --device=espmesh-02 --device-region=$REGION_NAME --device-registry=$REGISTRY_NAME --gateway=$GATEWAY_NAME --gateway-region=$REGION_NAME --gateway-registry=$REGISTRY_NAME --project=$PROJECT_ID
   ```

## Register Gateway

1. Open cloud shell, set the environment variables
2. Set the GATEWAY_NAME using `export GATEWAY_NAME="test-gateway"`
3. Execute: 
   
   ```sh
   gcloud iot devices create test-gateway   --region=asia-east1   --registry=dfpl-temp   --auth-method=association-only   --device-type=gateway   --project=$PROJECT_ID   --public-key path=rsa_cert.pem,type=rsa-x509-pem
   ```

## Other commands:

### To output the last 20 telemetry lines:

`gcloud pubsub subscriptions pull --auto-ack $PUBSUB_SUBSCRIPTION --limit=20`

### To access archival database

1. Open the url: `https://console.cloud.google.com/bigquery`
2. Select your project, the database name, and the table.
   
   ![Big Query Database](../master/documentation/imgs/bq.png?raw=true)


## Project Setup (Already done, no need to do it again)

1. Make sure that billing is enabled for your Google Cloud project. See [link](https://cloud.google.com/billing/docs/how-to/modify-project)

2. Enable the Cloud IoT Core and Cloud Pub/Sub APIs. [Enable APIs](https://console.cloud.google.com/flows/enableapi?apiid=cloudiot.googleapis.com,pubsub)

3. Execute the following commands:

    ```sh
    gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:cloud-iot@system.gserviceaccount.com --role=roles/pubsub.publisher
    
    gcloud pubsub topics create $PUBSUB_TOPIC
    
    gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTIO --topic $PUBSUB_TOPIC
    
    gcloud iot registries create $REGISTRY_NAME   --region=$REGION_NAME --event-notification-config=topic=$PUBSUB_TOPIC --enable-mqtt-config --enable-http-config
    ```

4. Generate your signing keys using the following commands, remember the location of the created key (`rsa_cert.pem`), they will be used to register a gateway :

    ```sh
    openssl req -x509 -newkey rsa:2048  -nodes  -keyout rsa_private.pem -x509 -days 365 -out rsa_cert.pem -subj "/CN=unused"
    ```
