# Example 2a Metrics Collection (Event Index)

This example will create a Cloud Schedule which triggers the Metrics Function (via a PubSub Topic). The function will send the metrics into Splunk HEC as an Event format (into an Event index). The script will also create a retry PubSub Topic, and set up a Function to retry any failed messages to HEC. 
(If you have already created any other examples, the Cloud Schedule and PubSub Trigger topic doesn't need to be re-created)

#### PubSub Topics:

**ExampleRetryTrigger** : This topic is common between all functions and triggers retries based on Cloud Schedule

**ExamplePubSubRetryTopic** : This topic can be common between all functions. This topic will collect failed writes from the Functions to HEC

**ExampleRetryTrigger** : This topic can be common between all functions and triggers retries based on Cloud Schedule



#### GCP Functions:

**ExampleMetricsEventFunction** : Function to pull sample of metrics from compute. Formatted as an Event into HEC

**ExampleEventsRetryTopic** : Retry Function to pull any failed messages from ExampleMetricsFunction


#### Cloud Scheduler

**ExampleMetricsSchedule** : Schedule for Running Events (5mins)
**ExampleRetry** : Retry Schedule (10mins)


## CLI Example

(run in bash or the Cloud Shell)

**Note that you will need to change values in bold in the scripts below to identify your project id, Log-Sink Service Account, HEC URL and HEC Token**
You can also change the OS environment variables in the first section to fit your needs

<pre>

#set OS environment variables for script. Change these for your deployment

MY_PROJECT=<strong>MY_PROJECT</strong>
METRICS_FUNCTION=ExampleMetricsEventsFunction
METRICS_TRIGGER=ExampleMetricsTriggerTopic
METRICS_SCHEDULE=ExampleMetricsSchedule

HEC_URL=<strong>URL-OR-IP-AND-PORT-FOR-HEC</strong>
METRICS_TOKEN=<strong>TOKEN-0000-0000-0000-0000</strong>

RETRY_FUNCTON=ExamplePubSubRetry
RETRY_TOPIC=ExamplePubSubRetryTopic
RETRY_SUBSCRIPTION=ExamplePubSubRetryTopic-sub
RETRY_TRIGGER_PUBSUB=ExampleRetryTrigger
RETRY_SCHEDULE=ExampleRetrySchedule


#This Schedule and topic only needs to be created once for all metrics functions unless you want different schedules. 
#Note:Match the schedule to the value in the TIME_INTERVAL environment variable below
#This example assumes a 5 minute schedule

#This Schedule and topic only needs to be created once for all metrics functions unless you want different schedules. 
#Note:Match the schedule to the value in the TIME_INTERVAL environment variable below
#This example assumes a 5 minute schedule

gcloud pubsub topics create $METRICS_TRIGGER

gcloud scheduler jobs create pubsub $METRICS_SCHEDULE --schedule "*/5 * * * *" --topic $METRICS_TRIGGER --message-body "RunMetric" --project $MY_PROJECT

# ..End of common Metric trigger section

#the clone command only needs to be done once for all of the examples
git clone https://github.com/splunk/splunk-gcp-functions.git


cd splunk-gcp-functions/Metrics

#create function

#this could be replaced by a static yaml file with the env variables set:

echo -e "HEC_URL: $HEC_URL\\nHEC_TOKEN: $METRICS_TOKEN\\nPROJECTID: $MY_PROJECT\\nTIME_INTERVAL: '5'\\nRETRY_TOPIC: $RETRY_TOPIC\\nMETRICS_LIST: '[\"compute.googleapis.com/instance/cpu/utilization\",\"compute.googleapis.com/instance/disk/read_ops_count\",\"compute.googleapis.com/instance/disk/write_bytes_count\",\"compute.googleapis.com/instance/disk/write_ops_count\",\"compute.googleapis.com/instance/network/received_bytes_count\",\"compute.googleapis.com/instance/network/received_packets_count\",\"compute.googleapis.com/instance/network/sent_bytes_count\",\"compute.googleapis.com/instance/network/sent_packets_count\",\"compute.googleapis.com/instance/uptime\"]'" > EnvEVars.yaml

gcloud functions deploy $METRICS_FUNCTION --runtime python37 \
--trigger-topic=$METRICS_TRIGGER --entry-point=hello_pubsub --allow-unauthenticated \
--env-vars-file EnvEVars.yaml


#This is a common section for all examples
#Doesn't need to be repeated for all unless you wish to have separate PubSub Topics for retrying different events.

gcloud pubsub topics create $RETRY_TOPIC

gcloud pubsub subscriptions create --topic $RETRY_TOPIC $RETRY_SUBSCRIPTION --ack-deadline=30
cd ../Retry

#create Retry function

gcloud functions deploy $RETRY_FUNCTON --runtime python37 \
 --trigger-topic=$RETRY_TRIGGER_PUBSUB --entry-point=hello_pubsub --allow-unauthenticated --timeout=240\
 --set-env-vars=PROJECTID=$MY_PROJECT,SUBSCRIPTION=$RETRY_SUBSCRIPTION

gcloud pubsub topics create $RETRY_TRIGGER_PUBSUB

gcloud scheduler jobs create pubsub $RETRY_SCHEDULE --schedule "*/10 * * * *" --topic $RETRY_TRIGGER_PUBSUB --message-body "Retry" --project $MY_PROJECT


</pre>