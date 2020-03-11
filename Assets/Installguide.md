# GCP Cloud Functions – Installation / Setup Guide

# Assets Function 
(0.2)

## **Pre-requisites**
HEC set-up on a Splunk instance (load balancer needed for a cluster) 
(note that if the over-ride token/URL has been set in the function environment variables, the destination for this must match where the source of the failed function originated)
This function will require a sourcetype to be created on your Splunk instance. An example sourcetype is available in props.conf in this folder.
This function requires Cloud Functions API to be enabled.
This function requires Cloud Assets API to be enabled on the Project you will be requesting the Asset inventory from. (https://cloud.google.com/asset-inventory/docs/quickstart and click on <ENABLE THE CLOUD ASSET INVENTORY API>)
This function requires Cloud Scheduler API to be enabled on the Project. (https://cloud.google.com/scheduler/docs/setup and click on the link on the bottom <ENABLE THE CLOUD SCHEDULER API>). Also make sure Cloud Scheduler has an assigned default region.
Set up a PubSub Topic for error/re-try of messages from the functions.  Note the name of the topic -  this will be used for Environment variables for the functions.
Set up a PubSub Trigger Topic (note that this topic is only going to be used as a trigger, with no events being sent there)
Create a Cloud Schedule, triggering the Assets PubSub Topic. Schedule this for how frequent you wish to request an Asset Inventory (e.g. 2hrs, 24hrs)


## **Function Dependencies:**

This function needs to be used with the GCS Function to read the Asset Inventory into Splunk HEC

## **Install with gcloud CLI**


*Suggestion: It may be easier to start with the full Example script provided in the Examples folder as it will create most of the pre-requisites and supporting entities - https://github.com/splunk/splunk-gcp-functions/blob/master/Examples/Example-4-Assets.md*


(run in bash or the Cloud Shell)

git clone https://github.com/splunk/splunk-gcp-functions.git

cd splunk-gcp-functions/Asset

gcloud functions deploy **myAssetFunction** --runtime python37 --trigger-topic=**ASSETS_TRIGGER_TOPIC** --entry-point=hello_pubsub --allow-unauthenticated --timeout=120 --set-env-vars=PROJECTID='**Project-id**',GCS_FILE_PATH='**Path-and-prefix-to-GCS-Bucket**'

** *Update the bold values with your own settings* **

*Note that the above example does not identify or send the data to Splunk HEC - the GCS Function should be added to do this*



## **Manual Setup**

1.	Create a new Cloud Function
2.	Name your function
3.	Set the Trigger to be Cloud Pub Sub 
4.	Select the Asset Trigger Trigger Topic from PubSub
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

## **Function Environment Variables**

<table><tr><td><strong>Variable</strong></td><td><strong>Value</strong></td></tr>
<tr><td>PROJECTID</td><td>Project ID for where the Retry Topic exists</td></tr>
<tr><td>GCS_FILE_PATH</td><td>GCS path to bucket where the Assets inventory will be written. 
<br>Enter the full path and initial prefix to this bucket and object - eg. gs://my_asset_bucket_for_project/asset_file<br>
Note that unixtime will be added to the filename on writing from the function</td></tr>
</table>




