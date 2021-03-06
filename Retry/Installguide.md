# GCP Cloud Functions – Installation / Setup Guide

# RetryEvent Function 
(0.1.5)

### **Pre-requisites**
HEC set-up on a Splunk instance (load balancer needed for a cluster) 
(note that if the over-ride token/URL has been set in the function environment variables, the destination for this must match where the source of the failed function originated)
Install GCP Add-On https://splunkbase.splunk.com/app/3088/ (uses the same sourcetypes defined in the add-on)
Set up a PubSub Topic for error/re-try of messages from the functions.  Note the name of the topic -  this will be used for Environment variables for the functions.
Set up Stackdriver log subscription for the PubSub error Topic
Create a Retry Trigger PubSub Topic (note that this topic is only going to be used as a trigger, with no events being sent there)
Create a Cloud Schedule, triggering the Retry PubSub Topic. Schedule this for how frequent you wish to “flush” out any events that failed to send to Splunk (e.g. 10 or 15mins)

### **Setup**

1.	Create a new Cloud Function
2.	Name your function
3.	Set the Trigger to be Cloud Pub Sub 
4.	Select the Retry Trigger Topic from PubSub
5.	Add the code:
6.	Select Inline editor as source
7.	Select the Runtime as Python 3.7
8.	Copy the function code into the main.py
9.	Copy the requirements.txt contents into the requirements.txt tab
10.	Click on “Show variables like environment, networking, timeouts and more” to open up more options
11.	Select the region where you want the function to run
12.	Increase the timeout for this function to 120
13.	Click on the + Add variable to open up the Environment variables entry
14.	Add the Environment variables and values described in the table below
15.	Click Deploy

### **Function Environment Variables**

<table><tr><td><strong>Variable</strong></td><td><strong>Value</strong></td></tr>
<tr><td>PROJECTID</td><td>Project ID for where the Retry Topic exists</td></tr>
<tr><td>SUBSCRIPTION</td><td>Name of the subscription that pulls from the Retry/Error PubSub Topic.</td></tr>
<tr><td>RETRY_TRIGGER_TOPIC</td><td>Name of the Retry Trigger Topic that triggers the function. Used to spawn more re-tries.</td></tr>
<tr><td>HEC_URL</td><td>OVER-RIDE Hostname/IP address and port number for URL for Splunk HEC (Load balancer required for cluster)
e.g. mysplunkinstance.splunk.com:8088 or 113.114.115.192:8088
This will point the destination of the message to a different URL to the originating message
Default is original message URL. <strong>Do not set if you wish to keep original destination</strong></td></tr>
<tr><td>HEC_TOKEN</td><td>HEC Token to OVER-RIDE the original destination for the event. Generate on Splunk instance. 
Note that this should be set on the Splunk side to be the same Index-type the token used for the function that is using this as a retry i.e. if a metrics index was the destination of the original, this over-ride token should indicate a metrics index also
Default is original message Token. <strong>Do not set if you wish to keep original destination</strong></td></tr>
<tr><td>EVENT_TYPE</td><td>Only Set if HEC_TOKEN and HEC_URL are set to over-ride the original event. Valid values: METRICS, EVENT, RAW
<br>METRIC : use this for Metrics going into Metrics index
<br>EVENT : use this for Metrics going into Event index
<br>RAW : use this for GCS Function re-try. 
<br><strong>Do not set if you wish to keep to the original destination</strong></td></tr>
<tr><td>BATCH</td><td>Number of events to pull from Retry PubSub in one call. Note that higher numbers here will potentially result in a higher execution time. Take care not to set this too high - you may need to make the pubsub subcription Acknowledgement deadline for the retry topic higher if this is set to a large number (>200) and also adjust the function timeout to accomodate. General guidance is the function can recall approx 40k pubsub events in 5 minutes function call with a 256M Function allocation (multiple spawned functions)<br>Default = 100 (Recommended)</td></tr>
<tr><td>TIMEOUT</td><td>Time in seconds for the function to stop pulling from Retry PubSub in one call (unless there are no events to retry). Note that if this is set higher than the function timeout, the function potentially will exit with a timeout - this could also result in some messages being sent more than once to Splunk. Guideance is to be same value as function timeout. Note: To avoid function timeouts where possible, the actual max execution will generally aim to be a few seconds less than the value set here.<br>Default = 240 </td></tr>
</table>

## Usage Note
This function may require tuning of settings to ensure a timely recovery of failed events.
The main settings to consider are:
- Function Timeout. Make sure that this is set large enough to give time for the function to retrieve the messages and send to Splunk. 
- PubSub Subcription Acknowledgement deadline. Make sure that this is set long enough so that it accepts acknowledgement of sending to Splunk. Setting this too small may result in duplication of events being sent to Splunk. Recommendation of 2 mins.
- BATCH Variable. This determines how many events are retrieved from the PubSub Topic in one API call. As the API can be expensive in execution time. Setting this too large can result in a limited amount of API calls in the timeframe that the function has to execute (Function Timeout), but setting too small can result in loss of time taken to execute the API call.
- TIMEOUT. This setting is useful to allow the function to know when the Function Timeout will occur (the function itself has no understanding of the function timeout setting). The function will attempt to maximise the time available without reaching the function timeout, which will save duplication of retrieving/sending and end result of duplicates events in Splunk. 
- Memory Usage. This is the least impacting setting. Increasing this will only benefit due to the CPU capacity given to the function. Improves slightly the time taken to send to HEC.

## Install with gcloud CLI

*Suggestion: It may be easier to start with one of the full Example scripts provided in the Examples folder as they will create most of the pre-requisites and supporting entities - https://github.com/splunk/splunk-gcp-functions/blob/master/Examples*

(run in bash or the Cloud Shell)

git clone https://github.com/pauld-splunk/splunk-gcp-functions.git

cd splunk-gcp-functions/Retry

gcloud functions deploy **myRetryEventFunction** --runtime python37 --trigger-topic=**RETRY_TRIGGER_TOPIC** --entry-point=hello_pubsub --allow-unauthenticated --timeout=120 --set-env-vars=PROJECTID='**Project-id**',SUBSCRIPTION='**Retry_PubSub_Subscription**',RETRY_TRIGGER_TOPIC='**RETRY_TRIGGER_TOPIC**'

** *Update the bold values with your own settings* **

*Note that the above example does not over-ride the destination URL or HEC token*

