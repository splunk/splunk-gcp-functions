# Troubleshooting / Common Issues

**When running the scripts first time, there is an error *ERROR: (gcloud.scheduler.jobs.create.pubsub) Could not determine the location for the project. Please try again.***

This error will occur if your Cloud Scheduler hasn't been run/enabled before. Go to the console and create a new schedule - it will ask for a region you wish to run the Project in. Once this is done, clean up the example and re-try the example scripts.

**I'm not getting any data into Splunk**

1) Check that the URL and HEC token are valid. 
	Try running this curl command (with the relevant url/token) to see if you can send into Splunk HEC
	<pre>curl -k "https://mysplunkserver.example.com:8088/services/collector" \
    -H "Authorization: Splunk CF179AE4-3C99-45F5-A7CC-3284AA91CF67" \
    -d '{"event": "Hello, world!", "sourcetype": "manual"}' </pre>
2) Check that your HEC_URL environment variable is correct. You don't need /services/collector for example. Just use  IPaddress:Port or Hostname:Port. Note that for Splunk Cloud customers, there is a specific URL for HEC - this is usually in the format of http-inputs-mysplunkcloud.splunkcloud.com. (There is no need for a port number). 
3) Do not use the ACK on the HEC settings

**My PubSub Function is hitting maximum executions limit - what's gone wrong?**

This is likely to be caused by the PubSub Function ingesting its own logs. This will cause an infinate loop / race. To stop this, edit the Log Export / Sink that the PubSub topic is subscribing to and make sure the filter excludes the PubSub Function from its logs. An easy way to resolve this is by using the filter resource.labels.function_name!=ExamplePubSubFunction (changing the name to your function name). 
Another possibilty is that your log export filter is too broad, and the number of of events is very large. Consider your filter design, and create more than one pubsub function if necessary to read from different topics/log exports to reduce the load on one function.


**My metrics has a gap between groups of metrics in Splunk**

This is normally caused by the Metrics Schedule and the Interval setting (TIME_INTERVAL) for the Metrics functions not being the same. For example, the schedule is 10mins whereas the metrics interval is 5. The TIME_INTERVAL setting should match that of the Schedule period.
If the settings are the same, then examine the function log and search for errors - if you see function timeouts or memory limit exceeded, this indicates that you need to increase the memory allocated to the function and function timeout (usually due to a large number of metrics being requested). Alternatively, reduce the time interval, and the number of metrics for the function (for example, split the list over more than one function).

**I have no metrics arriving in Splunk**

If you want to sent your metrics to a metrics index, make sure that your HEC input specifies a metrics index.
Also note the previous issue, where increasing the memory allocation and timeout for your function may resolve the issue (and/or reduce TIME_INTERVAL).

**Some of my events in Splunk are not complete / truncated**

This usually occurs due to the size of the event coming from Stackdriver - if they are very large, they will be truncated if you have only the default settings for TRUNCATE on the sourcetype (set to 10000). Some of the container logs for example can be 16K. You should update your sourcetype to add TRUNCATE=0.

**My events from GCS are not being split properly in Splunk**

This is usually down to your sourcetype for the HEC input not being set properly, or you have multiple sourcetypes going into the same GCS bucket. The Function currently only supports one sourcetype per GCS Bucket. Make sure you have the correct sourcetype on the HEC input setting.
The other potential issue is that you have not set the LINE_BREAKER regex environment variable in the function settings. By default, it will break events up from the file by newline only. If you have multi-line events, make sure you set the LINE_BREAKER to have the same regex values as the Splunk sourcetype's settings in props.conf (you may need to consult with your Splunk admin). It is important also to make sure to set BEFORE=TRUE if the break is done before the LINE_BREAKER regex.

**My events are not evenly distributed across my indexer cluster**

This is typically down to 2 reasons:
1) Your Load Balancer has been set to have sticky sessions. Disable this if possible
2) You are only sending events to one indexer (one HEC URL which is one of the Indexers). If you don't have a Load balancer, consider using a Heavy Forwarder in front of your Indexer cluster, as the functions currently only support sending to 1 HEC URL per function.

