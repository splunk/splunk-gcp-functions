# GCP Functions Library for Ingesting into Splunk

**Retry Functions**

This function periodically requests any failed events that were sent to a PubSub Retry Topic, and re-tries sending those events/metrics to HEC. The retry function can be collectively used for all of the functions, regardless of the source. If there is a subsequent failure to send to Splunk, the functions will not acknowledge the pull from PubSub, and therefore will be re-tried at a later attempt.
