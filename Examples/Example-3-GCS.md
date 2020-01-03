# Example 3: GCS Function

This example will create 2 PubSub Topics, create the GCS Function with a Retry Function, and a GCS example bucket. A Cloud Schedule is also created to trigger the Retry Function (via PubSub Topic). Note that the Schedule and Retry Trigger and Retry Topic is common between all of examples and doesn't need to be repeated if you build more than one example.


#### PubSub Topics Created:

**ExamplePubSubRetryTopic** : This topic can be common between all functions. This topic will collect failed writes from ExamplePubSub to HEC

**ExampleRetryTrigger** : This topic can be common between all functions and triggers retries based on Cloud Schedule

#### GCP Functions Created:

**ExampleGCS** : GCS Function pulling from an ExampleBucket 

**ExampleRetry** : Retry Function to pull any failed messages from ExamplePubSub (can be re-used across all examples)

## GCS Bucket

**example-bucket-xxxx** : Example GCS Bucket - note you will need to change the name to make sure that the bucket name is globally unique.


## CLI Example Scripts
(run in bash or the Cloud Shell)

**Note that you will need to change values in bold in the scripts below to identify your project id, GCS Bucket, HEC URL and HEC Token**
You can also change the OS environment variables in the first section to fit your needs

<pre>

#set OS environment variables for script. Change these for your deployment

MY_PROJECT=<strong>MY_PROJECT</strong>
GCS_FUNCTION=ExampleGCSFunction

GCS_BUCKET=<strong>example-bucket-xxxx</strong>/

HEC_URL=<strong>URL-OR-IP-AND-PORT-FOR-HEC</strong>
GCS_TOKEN=<strong>TOKEN-0000-0000-0000-0000</strong>

RETRY_FUNCTON=ExamplePubSubRetry
RETRY_TOPIC=ExamplePubSubRetryTopic
RETRY_SUBSCRIPTION=ExamplePubSubRetryTopic-sub
RETRY_TRIGGER_PUBSUB=ExampleRetryTrigger
RETRY_SCHEDULE=ExampleRetrySchedule

#this section is specific for this example only; give the bucket a global unique id

gsutil mb gs://$GCS_BUCKET


#the clone command only needs to be done once for all of the examples
git clone https://github.com/splunk/splunk-gcp-functions.git

cd splunk-gcp-functions/GCS

#create function

gcloud functions deploy $GCS_FUNCTION --runtime python37 \
  --trigger-bucket=$GCS_BUCKET --entry-point=hello_gcs \
  --allow-unauthenticated \
  --set-env-vars=HEC_URL=$HEC_URL,HEC_TOKEN=$GCS_TOKEN,PROJECTID=$MY_PROJECT,RETRY_TOPIC=$RETRY_TOPIC


#This is a common section for all examples
#Doesn't need to be repeated for all unless you wish to have separate PubSub Topics for retrying different events.

gcloud pubsub topics create $RETRY_TOPIC

gcloud pubsub subscriptions create --topic $RETRY_TOPIC $RETRY_SUBSCRIPTION --ack-deadline=240
cd ../Retry

#create Retry function

gcloud functions deploy $RETRY_FUNCTON --runtime python37 \
 --trigger-topic=$RETRY_TRIGGER_PUBSUB --entry-point=hello_pubsub --allow-unauthenticated --timeout=240\
 --set-env-vars=HEC_URL=PROJECTID=$MY_PROJECT,SUBSCRIPTION=$RETRY_SUBSCRIPTION,RETRY_TRIGGER_TOPIC=$RETRY_TRIGGER_PUBSUB

gcloud pubsub topics create $RETRY_TRIGGER_PUBSUB

gcloud scheduler jobs create pubsub $RETRY_SCHEDULE --schedule "*/10 * * * *" --topic $RETRY_TRIGGER_PUBSUB --message-body "Retry" --project $MY_PROJECT

</pre>
