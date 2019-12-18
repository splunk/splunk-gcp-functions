# GCP Cloud Functions – Installation / Setup Guide

## Metrics Function 
(version 0.5.8)

## **Function Flow process**

**Normal Flow:**
Cloud Schedule -> PubSub Topic (Trigger) -> GCP Function(->Pull from Stackdriver API)-> HEC

**Error Flow:** 
Cloud Schedule -> PubSub Topic (Trigger) -> GCP Function(->Pull from Stackdriver API)-> PubSub Retry Topic
Cloud Schedule -> PubSub Topic (Trigger) -> GCP Function(->Pull from PubSub Retry Topic)-> HEC


## **Pre-requisites –**
HEC set-up on a Splunk instance (load balancer needed for a cluster)
HEC token/input MUST allow access to an appropriate index – if the function is creating event metrics, an event index is needed, or if the function is to send to metrics index, the token must be associated with a metrics index.
Install GCP Add-On https://splunkbase.splunk.com/app/3088/ (uses the same sourcetypes defined in the add-on)
This function requires Cloud Functions API to be enabled.
This function requires Cloud Scheduler API to be enabled on the Project. (https://cloud.google.com/scheduler/docs/setup and click on the link on the bottom <ENABLE THE CLOUD SCHEDULER API>). Also make sure Cloud Scheduler has an assigned default region.
Set up a PubSub Topic for error messages from an event based functions (PubSub Function, Metrics Events Function) OR if this will be generating metrics, a PubSub for metrics Note the name of the topic -  this will be used for Environment variables for the functions.
Set up Stackdriver log subscription for the PubSub error Topic
Create a Retry Trigger PubSub Topic (note that this topic is only going to be used as a trigger, with no events being sent there)
Create a Cloud Schedule, triggering the Retry PubSub Topic. Schedule this for how frequent you wish to “flush” out any events that failed to send to Splunk (e.g. 15mins)

## **Function Dependencies:**

Metrics Function requires the Retry Function.


## **Install with gcloud CLI**

(run in bash or the Cloud Shell)

git clone https://github.com/pauld-splunk/splunk-gcp-functions.git

cd splunk-gcp-functions/Metrics

gcloud functions deploy **myMetricsFunction** --runtime python37 --trigger-topic=**METRICS_TRIGGER_TOPIC** --entry-point=hello_pubsub --allow-unauthenticated --env-vars-file **EnvironmentVariablesFile.yaml**

***Update the bold values with your own settings***
(The command above uses the basic list of environment variables, using defaults)

## **Manual Setup**

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
12.	Click on the + Add variable to open up the Environment variables entry
13.	Add the Environment variables and values described in the table below
14.	Click Deploy

## **Function Environment Variables**

<table><tr><td><strong>Variable</strong></td><td><strong>Value</strong></td></tr>
<tr><td>HEC_URL</td><td>Hostname/IP address and port number for URL for Splunk HEC (Load balancer required for cluster)
e.g. mysplunkinstance.splunk.com:8088 or 113.114.115.192:8088</td></tr>
<tr><td>HEC_TOKEN</td><td>HEC Token for the input. Generate on Splunk instance.
Ideally this should be the same as the token used for the function that is using this as a retry
</td></tr>
<tr><td>PROJECTID</td><td>Project ID for where the Retry Topic exists</td></tr>
<tr><td>METRICS_LIST</td><td>A list of metrics for the function to pull. Enclose the comma separated list with square brackets. Use full names for the metrics. For example:
["compute.googleapis.com/instance/cpu/utilization","compute.googleapis.com/instance/disk/read_ops_count"]
</td></tr>
<tr><td>TIME_INTERVAL</td><td>Time interval for the function to retrieve metrics for (in minutes). This is retrospective – i.e a setting of 5 will retrieve metrics from the last 5 minutes. Running 5, 10 or 15 minute intervals is a recommended setting; larger values may cause function timeouts, in which case you will need to adjust the function timeout setting</td></tr>
<tr><td>HOST</td><td>Hostname you wish to give the event
Defaults to GCPMetricsFunction
</td></tr>
<tr><td>SPLUNK_SOURCETYPE</td><td>Sourcetype to assign to the events. Note that this is only used if the metric is going into an event index.
Defaults to google:gcp:monitoring
</td></tr>
<tr><td>METRIC_INDEX_TYPE</td><td>Sets the type of metrics index that is being sent to. This should be METRICS for metrics index, or EVENT for event index.The event format is compatible with the GCP Add-On metrics.
Defaults to EVENT
</td></tr>
<tr><td>RETRY_TOPIC</td><td>Name of Topic to send event/metric to on any failure scenario for the function</td></tr>
</table>

<strong>Note that if you have a long metrics list for one single Function, you may need to increase the memory allocated to the function. This may also require the function timeout to be increased, which also may be needed if the TIME_INTERVAL is long. 
</strong>


If a CLI is used for this function, the configuration for the environment variables needs to be put into a configuration yaml file due to the list of metrics. The example below assumes that the variables have been set in a file, whereas the examples include a script to create that file.


## Example Metrics lists

There are a significant number of metrics available from GCP. The example (Metrics 2a and 2b) will set up a simple list of compute metrics, but the Function environment variables can be edited to include many more. Here are some samples that can be used for the METRICS_LIST variable:

### Compute:

<pre>
["compute.googleapis.com/instance/cpu/utilization","compute.googleapis.com/instance/disk/read_ops_count","compute.googleapis.com/instance/disk/read_bytes_count","compute.googleapis.com/instance/disk/write_bytes_count","compute.googleapis.com/instance/disk/write_ops_count","compute.googleapis.com/instance/network/received_bytes_count","compute.googleapis.com/instance/network/received_packets_count","compute.googleapis.com/instance/network/sent_bytes_count","compute.googleapis.com/instance/network/sent_packets_count","compute.googleapis.com/instance/uptime","compute.googleapis.com/firewall/dropped_bytes_count","compute.googleapis.com/firewall/dropped_packets_count"]
</pre>

### Cloud Functions:

<pre>
["cloudfunctions.googleapis.com/function/active_instances","cloudfunctions.googleapis.com/function/execution_count","cloudfunctions.googleapis.com/function/execution_times","cloudfunctions.googleapis.com/function/network_egress","container.googleapis.com/container/cpu/utilization","container.googleapis.com/container/disk/bytes_used"]
</pre>

### Containers / Kubernetes

<pre>
["container.googleapis.com/container/cpu/utilization","container.googleapis.com/container/disk/bytes_used","container.googleapis.com/container/accelerator/duty_cycle","container.googleapis.com/container/accelerator/memory_total","container.googleapis.com/container/accelerator/memory_used","container.googleapis.com/container/accelerator/request","container.googleapis.com/container/cpu/reserved_cores","container.googleapis.com/container/cpu/usage_time","container.googleapis.com/container/disk/bytes_total","container.googleapis.com/container/disk/bytes_used","container.googleapis.com/container/disk/inodes_free","container.googleapis.com/container/disk/inodes_total","container.googleapis.com/container/memory/bytes_total","container.googleapis.com/container/memory/bytes_used","container.googleapis.com/container/uptime"]
</pre>

### Storage
<pre>
[storage.googleapis.com/api/request_count",storage.googleapis.com/network/received_bytes_count",storage.googleapis.com/network/sent_bytes_count",storage.googleapis.com/storage/object_count"]
</pre>

### Logging

<pre>
["logging.googleapis.com/billing/bytes_ingested","logging.googleapis.com/billing/monthly_bytes_ingested","logging.googleapis.com/byte_count","logging.googleapis.com/exports/byte_count","logging.googleapis.com/exports/error_count","logging.googleapis.com/exports/log_entry_count","logging.googleapis.com/log_entry_count","logging.googleapis.com/logs_based_metrics_error_count","logging.googleapis.com/metric_throttled","logging.googleapis.com/time_series_count"]
</pre>

### Monitoring

<pre>
["monitoring.googleapis.com/billing/bytes_ingested","monitoring.googleapis.com/stats/num_time_series","monitoring.googleapis.com/uptime_check/content_mismatch","monitoring.googleapis.com/uptime_check/error_code","monitoring.googleapis.com/uptime_check/http_status","monitoring.googleapis.com/uptime_check/request_latency"]
</pre>

### PubSub

<pre>
["pubsub.googleapis.com/snapshot/backlog_bytes","pubsub.googleapis.com/snapshot/backlog_bytes_by_region","pubsub.googleapis.com/snapshot/config_updates_count","pubsub.googleapis.com/snapshot/num_messages","pubsub.googleapis.com/snapshot/num_messages_by_region","pubsub.googleapis.com/snapshot/oldest_message_age","pubsub.googleapis.com/snapshot/oldest_message_age_by_region","pubsub.googleapis.com/subscription/ack_message_count","pubsub.googleapis.com/subscription/backlog_bytes","pubsub.googleapis.com/subscription/byte_cost","pubsub.googleapis.com/subscription/config_updates_count","pubsub.googleapis.com/subscription/mod_ack_deadline_message_count","pubsub.googleapis.com/subscription/mod_ack_deadline_message_operation_count","pubsub.googleapis.com/subscription/mod_ack_deadline_request_count","pubsub.googleapis.com/subscription/num_outstanding_messages","pubsub.googleapis.com/subscription/num_undelivered_messages","pubsub.googleapis.com/subscription/oldest_unacked_message_age_by_region","pubsub.googleapis.com/subscription/pull_ack_message_operation_count","pubsub.googleapis.com/subscription/pull_ack_request_count","pubsub.googleapis.com/subscription/pull_message_operation_count","pubsub.googleapis.com/subscription/pull_message_operation_count","pubsub.googleapis.com/subscription/push_request_count","pubsub.googleapis.com/subscription/push_request_latencies","pubsub.googleapis.com/subscription/sent_message_count","pubsub.googleapis.com/topic/message_sizes","pubsub.googleapis.com/topic/num_unacked_messages_by_region","pubsub.googleapis.com/topic/oldest_unacked_message_age_by_region"]
</pre>



