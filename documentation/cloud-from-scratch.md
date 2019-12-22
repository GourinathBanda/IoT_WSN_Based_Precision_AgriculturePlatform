# Cloud Setup from scratch

These steps are already performed. Ther is no need to do it again unless you have to.

1. Make sure that billing is enabled for your Google Cloud project. See [link](https://cloud.google.com/billing/docs/how-to/modify-project)

2. Enable the Cloud IoT Core and Cloud Pub/Sub APIs. [Enable APIs](https://console.cloud.google.com/flows/enableapi?apiid=cloudiot.googleapis.com,pubsub)

3. Execute the following commands:

    ```sh
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member=serviceAccount:cloud-iot@system.gserviceaccount.com \
        --role=roles/pubsub.publisher
    
    gcloud pubsub topics create $PUBSUB_TOPIC
    
    gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTIO --topic $PUBSUB_TOPIC
    
    gcloud iot registries create $REGISTRY_NAME \
        --region=$REGION_NAME \
        --event-notification-config=topic=$PUBSUB_TOPIC \
        --enable-mqtt-config \
        --enable-http-config    

    ```

4. Create a service account credentials (`bq-manager.json`) that will be used to manage archival storage.
   
   ```sh
    gcloud iam service-accounts create bq-manager
    
    gcloud projects add-iam-policy-binding $PROJECT_ID --member "serviceAccount:bq-manager@$PROJECT_ID.iam.gserviceaccount.com" --role "roles/bigquery.dataOwner"
    
    gcloud iam service-accounts keys create bq-manager.json --iam-account bq-manager@$PROJECT_ID.iam.gserviceaccount.com
   ```

5. Download this credentials file (`bq-manager.json`) to the gateway computer.
6. Generate your signing keys using the following commands, remember the location of the created key (`rsa_cert.pem`), they will be used to register a gateway :

    ```sh
    openssl req -x509 -newkey rsa:2048  -nodes  -keyout rsa_private.pem -x509 -days 365 -out rsa_cert.pem -subj "/CN=unused"
    ```
