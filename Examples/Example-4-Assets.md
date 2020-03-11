# Example 4: Assets Function

This example will create 3 PubSub Topics, create the Assets and a GCS Function with a Retry Function, a GCS example bucket. 2 Cloud Schedules are also created to trigger the Assets and Retry Functions (via PubSub Topic). Note that the Retry Schedule and Retry Trigger and Retry Topic is common between all of examples and doesn't need to be repeated if you build more than one example.

Note: This function requires Cloud Assets API to be enabled on the Project you will be requesting the Asset inventory from. Do this before deploying the functions.
Also, ensure that the Cloud Schedule is enabled before running the script. (create a dummy schedule to confirm this beforehand)

#### PubSub Topics Created:

**ExampleAssetsTopic** : This topic is created as a trigger for the function

**ExamplePubSubRetryTopic** : This topic can be common between all functions. This topic will collect failed writes from ExamplePubSub to HEC

**ExampleRetryTrigger** : This topic can be common between all functions and triggers retries based on Cloud Schedule

#### GCP Functions Created:

**ExampleAssets** : Function to call the Assets API

**ExampleGCSAssets** : GCS Function pulling from an ExampleAssetsBucket 

**ExampleRetry** : Retry Function to pull any failed messages from ExamplePubSub (can be re-used across all examples)

## GCS Bucket

**example-assets-bucket-xxxx** : Example GCS Bucket to store the Assets files - note you will need to change the name to make sure that the bucket name is globally unique.


## CLI Example Scripts
(run in bash or the Cloud Shell)

**Note that you will need to change values in bold in the scripts below to identify your project id, HEC URL, token and GCS Bucket**
You can also change the OS environment variables in the first section to fit your needs
Note to use your Project ID, and not Project Name / Number

When running the scripts the first time in a new project, if asked, accept the queries to create/initialise services

<pre>

#set OS environment variables for script. Change these for your deployment

MY_PROJECT=<strong>MY_PROJECT</strong>
ASSETS_FUNCTION=ExampleAssetsFunction
# remember to give the bucket a global unique id. The file bath contains the object prefix for the object created by the asset function
GCS_ASSETS_BUCKET=<strong>example-assets-bucket-xxxx</strong>/
GCS_FILE_PATH=gs://$GCS_ASSETS_BUCKET/<strong>example-assets</strong>
GCS_FUNCTION=ExampleGCSAssetsFunction

HEC_URL=<strong>URL-OR-IP-AND-PORT-FOR-HEC</strong>
ASSETS_TOKEN=<strong>TOKEN-0000-0000-0000-0000</strong>

ASSETS_SCHEDULE=ExampleAssetsSchedule
ASSETS_TRIGGER_PUBSUB=ExampleAssetsTrigger

RETRY_FUNCTON=ExamplePubSubRetry
RETRY_TOPIC=ExamplePubSubRetryTopic
RETRY_SUBSCRIPTION=ExamplePubSubRetryTopic-sub
RETRY_TRIGGER_PUBSUB=ExampleRetryTrigger
RETRY_SCHEDULE=ExampleRetrySchedule

#this section is specific for this example only; 

#make sure that the function has access to view the assets.
gcloud projects add-iam-policy-binding $MY_PROJECT \
  --member serviceAccount:$MY_PROJECT@appspot.gserviceaccount.com \
  --role roles/cloudasset.viewer

gsutil mb gs://$GCS_ASSETS_BUCKET

#the clone command only needs to be done once for all of the examples
git clone https://github.com/splunk/splunk-gcp-functions.git

cd splunk-gcp-functions/Assets

#create triggers
gcloud pubsub topics create $ASSETS_TRIGGER_PUBSUB

gcloud scheduler jobs create pubsub $ASSETS_SCHEDULE --schedule "0 */6 * * *" --topic $ASSETS_TRIGGER_PUBSUB --message-body "Assets" --project $MY_PROJECT


#create function
gcloud functions deploy $ASSETS_FUNCTION --runtime python37 \
  --trigger-topic=$ASSETS_TRIGGER_PUBSUB --entry-point=hello_pubsub \
  --allow-unauthenticated \
  --set-env-vars=PROJECTID=$MY_PROJECT,GCS_FILE_PATH=$GCS_FILE_PATH


cd ../GCS

#create function

gcloud functions deploy $GCS_FUNCTION --runtime python37 \
  --trigger-bucket=$GCS_ASSETS_BUCKET --entry-point=hello_gcs --timeout=120\
  --allow-unauthenticated --timeout=120\
  --set-env-vars=HEC_URL=$HEC_URL,HEC_TOKEN=$ASSETS_TOKEN,PROJECTID=$MY_PROJECT,RETRY_TOPIC=$RETRY_TOPIC,BEFORE=TRUE,LINE_BREAK='{"name":"//'


#This is a common section for all examples
#Doesn't need to be repeated for all unless you wish to have separate PubSub Topics for retrying different events.

gcloud pubsub topics create $RETRY_TOPIC

gcloud pubsub subscriptions create --topic $RETRY_TOPIC $RETRY_SUBSCRIPTION --ack-deadline=240
cd ../Retry

#create Retry function

gcloud functions deploy $RETRY_FUNCTON --runtime python37 \
 --trigger-topic=$RETRY_TRIGGER_PUBSUB --entry-point=hello_pubsub --allow-unauthenticated --timeout=240\
 --set-env-vars=PROJECTID=$MY_PROJECT,SUBSCRIPTION=$RETRY_SUBSCRIPTION,RETRY_TRIGGER_TOPIC=$RETRY_TRIGGER_PUBSUB

gcloud pubsub topics create $RETRY_TRIGGER_PUBSUB

gcloud scheduler jobs create pubsub $RETRY_SCHEDULE --schedule "*/10 * * * *" --topic $RETRY_TRIGGER_PUBSUB --message-body "Retry" --project $MY_PROJECT

</pre>
