export PROJECT_ID="dfpl-project-001"
export PUBSUB_TOPIC="iotcore-topic"
export PUBSUB_SUBSCRIPTION="iotcore-subscription"
export REGISTRY_NAME="dfpl-temp"
export REGION_NAME="asia-east1"
export GATEWAY_NAME="test-gateway"


gcloud auth login
gcloud services enable pubsub.googleapis.com
open "https://console.cloud.google.com/iot/api?project=$PROJECT_ID"
    

gcloud projects add-iam-policy-binding $PROJECT_ID   --member=serviceAccount:cloud-iot@system.gserviceaccount.com   --role=roles/pubsub.publisher


gcloud pubsub topics create $PUBSUB_TOPIC
gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTION --topic $PUBSUB_TOPIC


gcloud iot registries create $REGISTRY_NAME   --region=$REGION_NAME   --event-notification-config=topic=$PUBSUB_TOPIC   --enable-mqtt-config --enable-http-config
export DEVICE_NAME="esp8266-0"








export DEVICE_NAME="esp8266-00"
openssl ecparam -genkey -name prime256v1 -noout -out ec_private.pem
openssl ec -in ec_private.pem -pubout -out ec_public.pem
gcloud iot devices create $DEVICE_NAME   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --public-key="path=./ec_public.pem,type=es256"
openssl ec -in <private-key.pem> -noout -text
openssl ec -in ec_private.pem -noout -text
read EC key
gcloud pubsub subscriptions pull --auto-ack $PUBSUB_SUBSCRIPTION --limit=1
gcloud pubsub subscriptions pull --auto-ack $PUBSUB_SUBSCRIPTION --limit=20
gcloud config list
gcloud pubsub subscriptions pull --auto-ack $PUBSUB_SUBSCRIPTION --limit=20
echo $GOOGLE_CLOUD_PROJECT
openssl req -x509 -newkey rsa:2048   -nodes -keyout rsa_private.pem -x509 -days 365 -out rsa_cert.pem -subj "/CN=unused"
ls
cat README-cloudshell.txt 
   


gcloud iot devices create test-gateway   --region=asia-east1   --registry=dfpl-temp   --auth-method=association-only   --device-type=gateway   --public-key path=rsa_cert.pem,type=rsa-x509-pem
echo $GOOGLE_CLOUD_PROJECT
export GOOGLE_CLOUD_PROJECT="dfpl-project-001"
gcloud iot devices create test-gateway   --region=asia-east1   --registry=dfpl-temp   --auth-method=association-only   --device-type=gateway   --public-key path=rsa_cert.pem,type=rsa-x509-pem

gcloud iot devices create test-gateway   --region=asia-east1   --registry=dfpl-temp   --auth-method=association-only   --device-type=gateway   --public-key path=rsa_cert.pem,type=rsa-x509-pem
gcloud iot devices create test-gateway   --region=asia-east1   --registry=dfpl-temp   --auth-method=association-only   --device-type=gateway   --project=$PROJECT_ID   --public-key path=rsa_cert.pem,type=rsa-x509-pem
gcloud iot devices create $MDEVICE_NAME   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID





gcloud iot devices create $MDEVICE_NAME   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
export MDEVICE_NAME="espmesh-00"
export GATEWAY_NAME="test-gateway"
gcloud iot devices create espmesh-00   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
gcloud iot devices create espmesh-01   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
gcloud iot devices create espmesh-02   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
gcloud iot devices gateways bind   --device=espmesh-00   --device-region=$REGION_NAME   --device-registry=$REGISTRY_NAME   --gateway=$GATEWAY_NAME   --gateway-region=$REGION_NAME   --gateway-registry=$REGISTRY_NAME   --project=$PROJECT_ID
gcloud iot devices gateways bind   --device=espmesh-01   --device-region=$REGION_NAME   --device-registry=$REGISTRY_NAME   --gateway=$GATEWAY_NAME   --gateway-region=$REGION_NAME   --gateway-registry=$REGISTRY_NAME   --project=$PROJECT_ID
gcloud iot devices gateways bind   --device=espmesh-02   --device-region=$REGION_NAME   --device-registry=$REGISTRY_NAME   --gateway=$GATEWAY_NAME   --gateway-region=$REGION_NAME   --gateway-registry=$REGISTRY_NAME   --project=$PROJECT_ID
git clone https://github.com/googlecloudplatform/python-docs-samples







export GATEWAY_NAME="test-gateway"
 _NAME   --event-notification-config=topic=$PUBSUB_TOPIC   --enable-mqtt-config --enable-http-config
gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTION --topic=devices
gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTION --topic=$PUBSUB_TOPIC
gcloud pubsub subscriptions create help
gcloud pubsub subscriptions create --help
ls





export GATEWAY_NAME="test-gateway"
gcloud iot devices create espmesh-00   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway \
gcloud iot devices create espmesh-03   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
gcloud iot devices create espmesh-04   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
gcloud iot devices create espmesh-05   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
gcloud iot devices create espmesh-06   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
gcloud iot devices create espmesh-07   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
gcloud iot devices create espmesh-09   --region=$REGION_NAME   --registry=$REGISTRY_NAME   --device-type=non-gateway   --project=$PROJECT_ID
echo $REGION_NAME


