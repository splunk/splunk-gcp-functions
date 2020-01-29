# GCP Cloud Functions – Installation / Setup Guide

## Alert Function 
(version 0.0.1 Beta)

## **Function Flow process**

**Normal Flow:**
Stackdriver Alert -> WebHook -> GCP Function -> HEC

**Error Flow:** 
Stackdriver Alert -> WebHook -> GCP Function -> PubSub Topic (error:RetryTopic)
Cloud Schedule -> PubSub Topic (Trigger) -> GCP Function(->Pull from PubSub Retry Topic)-> HEC

## **Pre-requisites**

HEC set-up on a Splunk instance (load balancer needed for a cluster)
HEC token/input MUST allow access to all indexes noted in the environment variables if the default token index is being over-ridden
This function requires a sourcetype of google:gcp:alert to be set-up on the Splunk instance (see below)
This function requires Cloud Functions API to be enabled.
Set up Stackdriver Alert; create a Notification as a Web Hook to the URL of the Function
Set up a PubSub Topic for error messages (Note the name of the topic -  this will be used in the Environment variables later)

## **Function Dependencies:**
Alert Function requires the Retry Function. Install and set up the Retry Function first


## Install with gcloud CLI

This is a beta release. Cloud CLI scripts to follow shortly


## **Manual Setup**
1.	Create a new Cloud Function
2.	Name your function – note the url for the function - you will need it later for the Stackdriver Alert
3.	Set the Trigger to be HTTP
4.	Add the code:
5.	Select Inline editor as source
6.	Select the Runtime as Python 3.7
7.	Copy the function code into the main.py
8.	Copy the content of requirements.txt into the requirements.txt tab
9.	Click on “Show variables like environment, networking, timeouts and more” to open up more options
10.	Select the region where you want the function to run
11.	Click on the + Add variable to open up the Environment variables entry
12.	Add the Environment variables and values described in the table below
13.	Click Deploy
14.	You will need to install the Retry function if you wish to have a recovery for any events that failed to write to Splunk. See install guide for that function.
15. Create your Alert in Stackdriver. Set the Notification to send webhook to the url of the function

## **Function Environment Variables**

<table><tr><td><strong>Variable</strong></td><td><strong>Value</strong></td></tr>
<tr><td>HEC_URL</td><td>Hostname/IP address and port number for URL for Splunk HEC (Load balancer required for cluster)
e.g. mysplunkinstance.splunk.com:8088 or 113.114.115.192:8088</td></tr>
<tr><td>HEC_TOKEN</td><td>HEC Token for the input. Generate on Splunk instance.</td></tr>
<tr><td>PROJECTID</td><td>Project ID for where the Retry Topic exists</td></tr>
<tr><td>HOST</td><td>Host value that Splunk will assign for the Alert event. Defaults to GCP_Alert_Function</td></tr>
<tr><td>SPLUNK_SOURCETYPE</td><td>Sourcetype that will be given to the event (defaults to google:gcp:alert)</td></tr>
<tr><td>SPLUNK_SOURCE</td><td>If set, this will be assigned to the “Source” of the event. If not set, defaults to "Stackdriver Alert:policyname"</td></tr>
<tr><td>INDEX</td><td>If this is set, its value can be set to over-ride the HEC token index. (defaults to no value – i.e. HEC token set index name)</td></tr>
<tr><td>RETRY_TOPIC</td><td>Name of Topic to send event to on any failure scenario for the function</td></tr>
</table>



## **Sourcetype definition**

Add this stanza to your Splunk props.conf
<pre>
[google:gcp:alert]
category = Custom
pulldown_type = 1
DATETIME_CONFIG = 
INDEXED_EXTRACTIONS = json
LINE_BREAKER = ([\r\n]+)
AUTO_KV_JSON = false
KV_MODE=none
NO_BINARY_CHECK = true
disabled = false
TRUNCATE=0
</pre>



