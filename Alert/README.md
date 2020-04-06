# GCP Functions Library for Ingesting into Splunk

**Alert Function**

This function will be triggered by a Stackdriver Alert event that has been configured to send to a Webhook that is the url of this function, and packages it up into a Splunk event. The event is then sent to the Http Event Collector (HEC). 
If any faiures occur during sending the message to HEC, the event is posted back to a Pub-Sub Topic. A recovery function is provided in the library which is executed via a Cloud Scheduler trigger (PubSub). The recovery function will attempt to clear out the PubSub retry topic and send these events into HEC.



