# Example Configuration builds

The files here contain scripts can be executed to build a full sample configurations using all of the functions in this library. The following configurations are created:
(Note that there are some common sections for these examples, which do not need to be re-run if one of the other examples has been created. This is noted in the scripts)

To run the examples, you can either run directly from the Cloud Shell in the GCP console (click **>_** to activate Cloud Shell), or by downloading the SDK or Quickstart onto your host/local machine (see here - https://cloud.google.com/sdk/install)

Make sure you have installed git on the host running the example scripts (GCP's Cloud Shell already has this installed).

Please refer to the individual function documentation for any pre-requisites before running the examples.

## Example 1: PubSub 

This example will create 2 example Log Export Sinks, 2 PubSub Topics and use the PubSub Function with a Retry Function. A Cloud Schedule is also created to trigger the Retry Function (via PubSub Topic). Note that this Schedule and Topic is common between all of examples and doesn't need to be repeated if you build more than one example.

## Example 2a: Metrics Collection (Event Index)

This example will create a Cloud Schedule which triggers the Metrics Function (via a PubSub Topic). The function will send the metrics into Splunk HEC as an Event format (into an Event index). The script will also create a retry PubSub Topic, and set up a Function to retry any failed messages to HEC. 
If you have already created any other examples, the Cloud Schedule and PubSub Trigger topic doesn't need to be re-created.

## Example 2b: Metrics Collection (Metrics Index)

This example is a clone of example 2a, but this function will send the metrics into Splunk's Metrics Index. It creates a Cloud Schedule which triggers the Metrics Function (via a PubSub Topic). The script will also create a retry PubSub Topic, and set up a Function to retry any failed messages to HEC.
Note that in practice, only one Cloud Schedule would be needed for metrics unless there is a need to have different schedules/intervals. If you want to run both examples, the section to create the Cloud Schedule for Metrics and its trigger PubSub Topic can be ignored. In the same way, if you have already created any other examples, the Cloud Schedule and PubSub Trigger topic doesn't need to be re-created.


## Example 3: GCS

This example creates a Function that is trigged by an object being created in GCS. The script also creates a Retry Topic for any failed messages to Splunk HEC. A Retry Function is created to send any failed messages. It will also create a Cloud Schedule and PubSub Trigger - if you have already created any other examples, these don't need to be re-created.


## Example 4: Assets

The example creates a function to collect asset information periodically, writing this into a GCS Bucket. The function is triggered by a PubSub Topic (called via Cloud Schedule). The example also builds a GCS Function as per Exanmple 3 to collect this asset data and post to Splunk.

## Example Cleanup 

The Examples can be cleaned up by copying and saving the script in the cleanup page. Update the variables (bucket names) highlighted in the script. Note that if you have changed the variables in any way, remember to change these for the cleanup, otherwise you may have services or components remaining after runing the script. **Note that this is a destructive process that cannot be undone - take care not to delete buckets or topics that contain data you wish to keep.**

## What the Scripts create...

#### Log export Sinks:

<table><tr><td><strong>Sink</strong></td><td><strong>Description</strong></td><td><strong>Filter</strong></td></tr>
<tr><td>ExampleSinkFunctions</td><td>Selects all GCP Function logs. Important note that it filters out the PubSub Function!!</td><td>resource.labels.function_name!="ExamplePubSub"</td></tr>
<tr><td>ExampleSinkNoFunctions</td><td>Selects all Kubernetes/containers logs</td><td>protoPayload.serviceName="container.googleapis.com"</td></tr></table>

**Caution: With aggregated export sinks, you can export a very large number of log entries. Design your logs query carefully.**


#### PubSub Topics:

**ExamplePubSubLogsTopic** : This topic will collect logs from the export sinks

**ExamplePubSubRetryTopic** : This topic will collect failed writes from ExamplePubSub to HEC

**ExampleMetricsRetryTopic** : This topic will collect failed writes from ExampleMetricsFunction to HEC

**ExampleEventsRetryTopic** : This topic will collect failed writes from ExampleMetricsEventsFunction and ExampleAssets to HEC

**ExampleRawRetryTopic** : This topic will collect failed writes from ExampleGCSFunction to HEC

**ExampleAssetsRetryTopic** : This topic will collect failed writes from ExampleAssetFunction to HEC

#### GCP Functions:

**ExamplePubSub** : PubSub Function pulling from ExamplePubSubLogsTopic 

**ExamplePubSubRetry** : Retry Function to pull any failed messages from Functions

**ExampleMetricsFunction** : Function to pull sample of metrics from compute. Formatted as metrics index into HEC

**ExampleMetricsEventsFunction** : Mirror function to ExampleMetricsFunction, but sending metrics into a Splunk event index

**ExampleGCSFunction** : Function to pull sample objects from a bucket

**ExampleAssetFunction** : Function to pull asset information into HEC

#### Cloud Scheduler

**ExampleRetry** : Retry Schedule (10mins)
**ExampleAsset** : Schedule to run Asset list (12hrs)













