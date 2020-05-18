# GCS Function 
(Version 0.2.0)


## **Function Flow process**

**Normal Flow:**
GCS Object -> GCP Function -> HEC

**Error Flow:** 
GCS Object -> GCP Function -> PubSub Retry Topic

Cloud Schedule -> PubSub Topic (Trigger) -> GCP Function(->Pull from PubSub Retry Topic)-> HEC


## **Pre-requisites –**
HEC set-up on a Splunk instance (load balancer needed for a cluster)
HEC token/input MUST allow access to an index and specify a sourcetype for the log type being ingested. Note that all objects in the GCS bucket will be assigned both sourcetype and index per the token.
Splunk: sourcetype (event break/time) must be set on the receiving indexers. (Note – you will need to use the event breaker regex for this function setup)
This function requires Cloud Functions API to be enabled.
Set up a PubSub Topic for error messages (RETRY_TOPIC). Note the name of the topic -  this will be used in the Environment variables later. 
The Batch recovery function must be used for this function (not event), set with EVENT_TYPE as RAW – note also that the PubSub error topic needs to be ONLY for errors from functions with the same sourcetype/index HEC token; 
e.g. if the logs in bucket A has sourcetype B and the destination is a HEC destination C, and error PubSub Topic of D. The recovery function must use the same destination HEC destination C. If Bucket X also has the same sourcetype B, then it can also use the same PubSub error topic and recovery function. However, if another bucket Y has a sourcetype Z (or needs to go into a different index), it will need a separate error PubSub Topic and Recovery function.

## **Function Dependencies:**

PubSub Function requires the Retry Function 

## **Function Limits:**

The GCP functions have a memory capacity limit of 2GB. Therefore this function has a limitation of sending log files that smaller than 1G. Log files larger than this will cause the function to exit with a memory limit exceeded. Also make sure that the time out setting for the function is large enough for copying the file. 

## **Install with gcloud CLI**

*Suggestion: It may be easier to start with the full Example script provided in the Examples folder as it will create most of the pre-requisites and supporting entities - https://github.com/splunk/splunk-gcp-functions/blob/master/Examples/Example-3-GCS.md*

(run in bash or the Cloud Shell)

git clone https://github.com/splunk/splunk-gcp-functions.git

cd splunk-gcp-functions/GCS

gcloud functions deploy **myGCSFunction** --runtime python37 --trigger-bucket=**TRIGGER_BUCKET** --entry-point=hello_gcs --allow-unauthenticated --timeout=300 --memory=2048MB --set-env-vars=HEC_URL='**HOSTNAME_OR_IP_FOR_HEC**',HEC_TOKEN='**0000-0000-0000-0000**',PROJECTID='**Project-id**',RETRY_TOPIC='**Retry_Topic**'

***Update the bold values with your own settings***

(The command above uses the basic list of environment variables, with newline breaker)

## **Manual Setup**

1.	Create a new Cloud Function
2.	Name your function – note the name – see important note below on the log export
3.	Set the Trigger to be Cloud Storage
4.	Set Event Type as Finalize/Create
5.	Select a Bucket from GCS
6.	Add the code:
7.	Select Inline editor as source
8.	Select the Runtime as Python 3.7
9.	Copy the function code into the main.py
10.	Copy the requirements.txt contents into the requirements.txt tab
11.	Click on “Show variables like environment, networking, timeouts and more” to open up more options
12.	Select the region where you want the function to run
13.	Click on the + Add variable to open up the Environment variables entry
14.	Add the Environment variables and values described in the table below
15. Make sure you select the appropriate size'd Function Memory Allocation - if you are going to ingest large files, set to Max 2GB
16.	Click Deploy
17.	You will need to install the RetryBatch function if you wish to have a recovery for any events that failed to write to Splunk. See install guide for that function.

## **Function Environment Variables**

<table><tr><td><strong>Variable</strong></td><td><strong>Value</strong></td></tr>
<tr><td>HEC_URL</td><td>Hostname/IP address and port number for URL for Splunk HEC (Load balancer required for cluster)
e.g. mysplunkinstance.splunk.com:8088 or 113.114.115.192:8088</td></tr>
<tr><td>HEC_TOKEN</td><td>HEC Token for the input. Generate on Splunk instance.
(make note of HEC token requirements above)</td></tr>
<tr><td>LINE_BREAKER</td><td>Enter the regex for the line breaking for the events in the bucket objects. 
Defaults to \n (newline)</td></tr>
<tr><td>BEFORE</td><td>Set this to TRUE if you want to break BEFORE the line breaker, or FALSE if you want to break After the line breaker.
Defaults to FALSE</td></tr>
<tr><td>PROJECTID</td><td>Project ID for where the Retry Topic exists</td></tr>
<tr><td>RETRY_TOPIC</td><td>Name of Topic to send event to on any failure scenario for the function</td></tr>
<tr><td>BATCH</td><td>Size of Batch to send to HEC. Reduce this if you want less events per batch to be sent to Splunk. Default 32k</td></tr>
<tr><td>THREADS</td><td>Number of worker threads to send payload to HEC. Use only if issues with overload on HEC. Default 127 (i.e. 128 threads)</td></tr>
</table>





