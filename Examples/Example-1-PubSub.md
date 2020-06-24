# Example 1: PubSub

This example will create 2 example Log Export Sinks, 3 PubSub Topics and use the PubSub Function with a Retry Function. A Cloud Schedule is also created to trigger the Retry Function (via PubSub Topic). Note that the Schedule and Retry Trigger and Retry Topic is common between all of examples and doesn't need to be repeated if you build more than one example.

#### Log export Sinks Created:

<table><tr><td><strong>Sink</strong></td><td><strong>Description</strong></td><td><strong>Filter</strong></td></tr>
<tr><td>ExampleSinkFunctions</td><td>Selects all GCP Function logs. Important note that it filters out the PubSub Function!!</td><td>resource.labels.function_name!="ExamplePubSub"</td></tr>
<tr><td>ExampleSinkNoFunctions</td><td>Selects all Kubernetes/containers logs</td><td>protoPayload.serviceName="container.googleapis.com"</td></tr></table>

**Caution: With aggregated export sinks, you can export a very large number of log entries. Design your logs query carefully.**


#### PubSub Topics Created:

**ExamplePubSubLogsTopic** : This topic will collect logs from the export sinks

**ExamplePubSubRetryTopic** : This topic can be common between all functions. This topic will collect failed writes from ExamplePubSub to HEC

**ExampleRetryTrigger** : This topic can be common between all functions and triggers retries based on Cloud Schedule

#### GCP Functions Created:

**ExamplePubSub** : PubSub Function pulling from ExamplePubSubLogsTopic 

**ExampleRetry** : Retry Function to pull any failed messages from ExamplePubSub (can be re-used across all examples)


## CLI Example Scripts
(run in bash or the Cloud Shell)

**Note that you will need to change values in bold in the scripts below to identify your project id, HEC URL and HEC Token**
You can also change the OS environment variables in the first section to fit your needs
Note to use your Project ID, and not Project Name / Number

When running the scripts the first time in a new project, if asked, accept the queries to create/initialise services

<pre>

#set OS environment variables for script. Change these for your deployment

MY_PROJECT=<strong>MY_PROJECT</strong>
PUBSUB_FUNCTION=ExamplePubSubFunction

PUBSUB_TOPIC=ExamplePubSubLogsTopic
PUBSUB_SINK1=ExampleSinkForFunctions
PUBSUB_SINK2=ExampleSinkNoFunctions

HEC_URL=<strong>URL-OR-IP-AND-PORT-FOR-HEC</strong>
PUBSUB_TOKEN=<strong>TOKEN-0000-0000-0000-0000</strong>

RETRY_FUNCTON=ExamplePubSubRetry
RETRY_TOPIC=ExamplePubSubRetryTopic
RETRY_SUBSCRIPTION=ExamplePubSubRetryTopic-sub
RETRY_TRIGGER_PUBSUB=ExampleRetryTrigger
RETRY_SCHEDULE=ExampleRetrySchedule



#this section is specific for this example only

gcloud pubsub topics create $PUBSUB_TOPIC

#create log-sinks...

#MAKE NOTE OF THIS SINK - IT ENSURES THAT THERE IS NO RECORDING OF THE FUNCTIONS OWN LOGS!!!

gcloud logging sinks create $PUBSUB_SINK1 \
  pubsub.googleapis.com/projects/$MY_PROJECT/topics/$PUBSUB_TOPIC \
  --log-filter="resource.labels.function_name!=$PUBSUB_FUNCTION"

LOG_SINK_SERVICE_ACCOUNT=`gcloud logging sinks describe $PUBSUB_SINK1 --format="value(writerIdentity)"`

#the last command will return the LOG_SINK_SERVICE_ACCOUNT 
gcloud pubsub topics add-iam-policy-binding $PUBSUB_TOPIC \
  --member $LOG_SINK_SERVICE_ACCOUNT  --role roles/pubsub.publisher

# THIS SINK WILL GET ALL LOGS OTHER THAN CLOUD FUNCTIONS - BEWARE IT MAY HAVE HIGH VOLUME!!!

gcloud logging sinks create $PUBSUB_SINK2 \
  pubsub.googleapis.com/projects/$MY_PROJECT/topics/$PUBSUB_TOPIC \
  --log-filter="resource.type!=cloud_function"

LOG_SINK_SERVICE_ACCOUNT=`gcloud logging sinks describe $PUBSUB_SINK2 --format="value(writerIdentity)"`

#the last command will return the LOG_SINK_SERVICE_ACCOUNT 
gcloud pubsub topics add-iam-policy-binding $PUBSUB_TOPIC \
  --member $LOG_SINK_SERVICE_ACCOUNT  --role roles/pubsub.publisher

#the clone command only needs to be done once for all of the examples
git clone https://github.com/splunk/splunk-gcp-functions.git

cd splunk-gcp-functions/PubSubFunction

#create function

gcloud functions deploy $PUBSUB_FUNCTION --runtime python37 \
  --trigger-topic=$PUBSUB_TOPIC --entry-point=hello_pubsub \
  --allow-unauthenticated \
  --set-env-vars=HEC_URL=$HEC_URL,HEC_TOKEN=$PUBSUB_TOKEN,PROJECTID=$MY_PROJECT,RETRY_TOPIC=$RETRY_TOPIC


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

gcloud scheduler jobs create pubsub $RETRY_SCHEDULE --schedule "*/5 * * * *" --topic $RETRY_TRIGGER_PUBSUB --message-body "Retry" --project $MY_PROJECT

</pre>
