# GCP Cloud Functions – Installation / Setup Guide

## PubSub Function 
(version 0.1.6)

## **Function Flow process**

**Normal Flow:**
Stackdriver Logging -> Logging Export -> PubSub Topic -> GCP Function -> HEC

**Error Flow:** 
Stackdriver Logging -> Logging Export -> PubSub Topic -> GCP Function -> PubSub Topic (error:RetryTopic)
Cloud Schedule -> PubSub Topic (Trigger) -> GCP Function(->Pull from PubSub Retry Topic)-> HEC

## **Pre-requisites**

HEC set-up on a Splunk instance (load balancer needed for a cluster)
HEC token/input MUST allow access to all indexes noted in the environment variables if the default token index is being over-ridden
Install GCP Add-On https://splunkbase.splunk.com/app/3088/ (uses the same sourcetypes defined in the add-on)
This function requires Cloud Functions API to be enabled.
This function requires Cloud Scheduler API to be enabled on the Project. (https://cloud.google.com/scheduler/docs/setup and click on the link on the bottom <ENABLE THE CLOUD SCHEDULER API>). Also make sure Cloud Scheduler has an assigned default region.
Set up Stackdriver logs; create an export(s) and subscription to a PubSub Topic (see important note below)
Set up a PubSub Topic for error messages (Note the name of the topic -  this will be used in the Environment variables later)

## **Function Dependencies:**
PubSub Function requires the Retry Function. Install and set up the Retry Function first


## Install with gcloud CLI

(run in bash or the Cloud Shell)

git clone https://github.com/splunk/splunk-gcp-functions.git

cd splunk-gcp-functions/PubSubFunction

gcloud functions deploy **myPubSubFunction** --runtime python37 --trigger-topic=**TRIGGER_TOPIC** --entry-point=hello_pubsub --allow-unauthenticated --set-env-vars=HEC_URL='**HOSTNAME_OR_IP_FOR_HEC**',HEC_TOKEN='**0000-0000-0000-0000**',PROJECTID='**Project-id**',RETRY_TOPIC='**Retry_Topic**'

***Update the bold values with your own settings***

(The command above uses the basic list of environment variables)


## **Manual Setup**
1.	Create a new Cloud Function
2.	Name your function – note the name – see important note below on the log export
3.	Set the Trigger to be Cloud Pub Sub 
4.	Select a Topic from PubSub
5.	Add the code:
6.	Select Inline editor as source
7.	Select the Runtime as Python 3.7
8.	Copy the function code into the main.py
9.	Copy the content of requirements.txt into the requirements.txt tab
10.	Click on “Show variables like environment, networking, timeouts and more” to open up more options
11.	Select the region where you want the function to run
12.	Click on the + Add variable to open up the Environment variables entry
13.	Add the Environment variables and values described in the table below
14.	In another browser window, check that the log export that is subscribed by the PubSub Topic has eliminated the name of the function. (see below)
15.	Click Deploy
16.	You will need to install the Retry function if you wish to have a recovery for any events that failed to write to Splunk. See install guide for that function.

## **Function Environment Variables**

<table><tr><td><strong>Variable</strong></td><td><strong>Value</strong></td></tr>
<tr><td>HEC_URL</td><td>Hostname/IP address and port number for URL for Splunk HEC (Load balancer required for cluster)
e.g. mysplunkinstance.splunk.com:8088 or 113.114.115.192:8088</td></tr>
<tr><td>HEC_TOKEN</td><td>HEC Token for the input. Generate on Splunk instance.</td></tr>
<tr><td>PROJECTID</td><td>Project ID for where the Retry Topic exists</td></tr>
<tr><td>HOST</td><td>Host value that Splunk will assign for the PubSub event. Defaults to GCPFunction</td></tr>
<tr><td>SPLUNK_SOURCETYPE</td><td>Sourcetype that will be given to the event (defaults to google:gcp:pubsub:message)</td></tr>
<tr><td>SPLUNK_SOURCE</td><td>If set, this will be assigned to the “Source” of the event. If not set, defaults to PubSub topic</td></tr>
<tr><td>INDEX</td><td>If this is set, its value can be set to over-ride the HEC token index. If this is set to LOGNAME then another environment variable with the name of the log needs to be set with an index name e.g. if you want all logs from “cloudaudit.googleapis.com%2Factivity” to be sent to index ActivityIX, you need to create an environment variable with the name “activity” with the value of ActivityIX. 
Note to use the value after “%2F”, or if the log doesn’t have that, use the value after /logs/ (eg. A logname of projects/projname/logs/OSConfigAgent would have variable set to OSConfigAgent)
Notes:HEC Token must have set access to the indexes noted here
Wildcard values are not accepted
(defaults to no value – i.e. HEC token set index name)</td></tr>
<tr><td>logname</td><td>A variable with a log name (ending only) will override the HEC token index for the event. Note that INDEX needs to be set to LOGNAME for this to be used. Use logname after /logs/ or if name has “%2F” in the name, use the logname after “%2F” 
Examples:
cloudaudit.googleapis.com%2Factivity -> use activity 
/logs/OSConfigAgent -> use OSConfigAgent
(defaults to no value)</td></tr>
<tr><td>COMPATIBLE</td><td>Set this to TRUE to maintain compatibility with Add-On. If not TRUE, event payload will be exact copy of PubSub event. Default is TRUE</td></tr>
<tr><td>RETRY_TOPIC</td><td>Name of Topic to send event to on any failure scenario for the function</td></tr>
</table>




## **PUB-SUB FUNCTION: IMPORTANT USAGE NOTE**

As the cloud function executes within GCP’s environment, its own logs are collected in Stacktdriver logs. If your Log Export collects logs from Cloud Functions **MAKE SURE YOU ELIMINATE THE FUNCTION NAME FROM THE EXPORT**. Logs for this function cannot be collected by itself! You will need another Function and log subscription to do this (i.e. one function monitoring the other)

For example, if your function name is GCP-Pub-Sub, and you wish to collect logs from other functions, then the Export Filter needs to include resource.labels.function_name!="GCP-Pub-Sub"

**Failure to do this will cause the function to race and max out function execution capacity in your project. (it is essentially logging itself, which then causes more logs to be created, causing a feedback race loop)**




