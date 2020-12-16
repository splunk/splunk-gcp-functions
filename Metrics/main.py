#GCPMetricsFunction v0.7.2
#All-in-one metrics function

'''MIT License
Copyright (c) 2019 Splunk
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: 
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. '''

import base64
import argparse
import os
import pprint
import time
import json
import re
import threading
from threading import Thread
from queue import Queue

from google.cloud import monitoring_v3
from datetime import datetime

from datetime import date

import time
import requests
from requests.adapters import HTTPAdapter
import urllib3
##turns off the warning that is generated below because using self signed ssl cert
urllib3.disable_warnings()


#threadsafe HEC Events list
class HECMessages:
    def __init__(self):
        self.HECevents = []
        self._lock = threading.Lock()

    def locked_update(self, HECevent):     
        with self._lock:
            self.HECevents.append(HECevent) 

"""Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload. 
         context (google.cloud.functions.Context): Metadata for the event.
         These values are ignored as used only as a Trigger for this function
"""

def hello_pubsub(event, context):
    
    HEC_Pack_size=20    # number of events per http post to HEC. Max size = 5MB by default on HEC
    now = time.time()
    #HECevents=[]
    HECevents=HECMessages() #create threadsafe message list
    
    metricslist=json.loads(os.environ['METRICS_LIST'])
    try:
        payloadType=os.environ['METRIC_INDEX_TYPE']
    except:
        payloadType='EVENT'
    #print(metricslist)
    
    workers=len(metricslist)
    if workers>8:
        workers=8
        
    metricsq=Queue()
    for x in range(workers):
        worker = BuilderThreadWorker(metricsq)
        # Set as daemon thread 
        worker.daemon = True
        worker.start()

    for metric in metricslist:
        metricsq.put((metric, now, HECevents,payloadType))

    #wait for all of the builds to complete
    metricsq.join()    
    
    message_counter=0
    package=''
    flushed=0
    
    workers=int(round(len(HECevents.HECevents)/HEC_Pack_size))
    queue = Queue()
    threadcount=10
    if workers<threadcount:
        threadcount=workers
    # Create (max) 10 worker threads (no need to thread more than number of packages)
    for x in range(threadcount):
        worker = HECThreadWorker(queue)
        # Set as daemon thread 
        worker.daemon = True
        worker.start()
    
    for events in HECevents.HECevents:
        package=package+events
        message_counter+=1
        if message_counter>HEC_Pack_size:
            #splunkHec(package);
            queue.put(package)
            message_counter=0;
            package=''
    
    if len(package)>0:
        #splunkHec(package);
        queue.put(package)
    
    # wait for the queue to finish processing all the tasks
    queue.join() 


class BuilderThreadWorker(Thread):

    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the parameters from the queue and expand the queue
            metric, now, HECevents,payloadType = self.queue.get()
            try:
                MetricBuilder(metric, now, HECevents,payloadType)
            finally:
                self.queue.task_done()
                
def MetricBuilder(metric,now,HECevents,payloadType):
    
    one_time_series = list_time_series(os.environ['PROJECTID'], metric, now, int(os.environ['TIME_INTERVAL']))

    source=os.environ['PROJECTID']+':'+metric
        
        
    for data in one_time_series:
    
        pointsStrList=str(data.points)
            
        strdata=str(data)
        metricKindPart=get_metric_kind(strdata)
        valueTypePart=get_value_type(strdata)    
        metricPart=str(data.metric)
        resourcePart=str(data.resource)

        pointsList=pullPointsList(pointsStrList)                    
        resourcePart=pull_labels(resourcePart,'"resource":{',1,1) 
        metricPart=pull_labels(metricPart,'"metric":{',1,1)

        numPoints=len(pointsList)/3
        ix=0
        getevent='NULL'
        while ix<numPoints:
            if pointsList[ix,2]!="-":     #ignore distributions with no values
                getevent = makeEvent(source,metricPart,resourcePart,metricKindPart,valueTypePart,pointsList[ix,0],pointsList[ix,1],pointsList[ix,2],now,payloadType)
            else:
                getevent='NULL'
            ix=ix+1
            if getevent!='NULL':
                HECevents.locked_update(getevent)

                
def makeEvent(source,metric,resource,metrickind,valuetype,points,timevalue,value,now,payloadType):

    try:
        host=os.environ['HOST']
    except:
        host='GCPMetricsFunction'
    
    try:
        sourcetype=os.environ['SPLUNK_SOURCETYPE']
    except:
        sourcetype='google:gcp:monitoring'

    if int(timevalue)<((now - int(os.environ['TIME_INTERVAL'])*60) - 180):     #filter out earlier events to avoid duplications
        HECevent='NULL'   
    else:
        if payloadType=='EVENT':
            HECevent='{"time": '+ timevalue + ', "host": "'+ host + '", "source": "'+source+'", "sourcetype": "'+sourcetype+'", "event":{'            
            HECevent=HECevent+points+','+metric+resource+metrickind+valuetype+'}}'
            HECevent=HECevent.replace('\n','')
        else: #metric
            HECevent='{"time":'+ timevalue+',"event":"metric","source":"'+source+'","host":"'+host+'","fields":{'
            metric=stripMetric(metric)
            resource=stripResource(resource)
            points=stripPoints(points)
            HECevent=HECevent+metrickind+resource+','+valuetype+','+metric+',"_value":'
            HECevent=HECevent+value+'}}'

    HECevent=HECevent.replace("\n","")        
    
    return HECevent

def stripMetric(in_str):
    
    start_pt=in_str.find('"metric":{"labels":{')
    if start_pt!=-1:
        start_pt=start_pt+21
    else: #there is only the metric, no labels
        start_pt=in_str.find('"type":')
    end_pt=len(in_str)-2
    ret_string=in_str[start_pt:end_pt]
    ret_string=ret_string.replace('type','metric_name')
    return ret_string.replace('}','')

def stripResource(in_str):
    #find the resource key:values for metrics index format only
    start_pt=in_str.find('"resource":{"labels":{')+23
    end_pt=len(in_str)-1
    in_str=in_str[start_pt:end_pt]
    in_str=in_str.replace('type','resourceType')
    return in_str.replace('}','')

def stripPoints(in_str):
    #this is for distribution values only - need to extract key:value pairs for metrics index
    start_pt=in_str.find('distributionValue')
    if start_pt>0: #distribution value - need to extract key:value pairs for metrics index
        start_pt=in_str.find('"count"',start_pt)
        end_pt=in_str.find(',',start_pt)
        ret_string=in_str[start_pt:end_pt]
        start_pt=in_str.find('"exponentialBuckets":{',end_pt)+23
        end_pt=in_str.find('}},',start_pt)-2
        ret_string=ret_string+in_str[start_pt]
    else:
        ret_string=''
    return ret_string


def list_time_series(project_id, metric_type, now_time, timelength):

    client = monitoring_v3.MetricServiceClient()
    project_name = client.project_path(project_id)
    interval = monitoring_v3.types.TimeInterval()
    now = now_time #time.time()
    interval.end_time.seconds = int(now)
    interval.end_time.nanos = int(
        (now - interval.end_time.seconds) * 10**9)
    interval.start_time.seconds = int(now - timelength*60) - 180
    interval.start_time.nanos = interval.end_time.nanos
    metric_string = 'metric.type = ' + '"'+metric_type+'"'

    results = client.list_time_series(
        project_name,
        metric_string, 
        interval,
        monitoring_v3.enums.ListTimeSeriesRequest.TimeSeriesView.FULL)
    return results


def uxtime(unixtime):
    return datetime.utcfromtimestamp(unixtime).strftime('%Y-%m-%dT%H:%M:%SZ')   


def pull_labels(in_string,initialstr,event,flag):
    #extract the labels from the payload, return json format
    returning=initialstr
    #get the type line
    start_type=in_string.find('type:')+5
    end_type=in_string.find('"',start_type+3)+1
    typestr=in_string[start_type:end_type]
    typestr='"type":'+typestr
    
    #get the key/value pairs from labels, cut them out of string
    cutstr=in_string
    start_k = cutstr.find('key:') + 4

    #make sure it has labels, if not, then only has type
    if (start_k>3):
        returning=returning+'"labels":{'   
        typeonly=1
    
    while (start_k!=3):
        end_k = cutstr.find('value:')-1
        start_v = end_k+8
        end_v= cutstr.find('}')-1
        returning=returning+cutstr[start_k:end_k]+':'+cutstr[start_v:end_v]
        cutstr=cutstr[end_v+2:]
        start_k = cutstr.find('key:') + 4
        if start_k>3: #if more keys, then add comma, otherwise, end of labels
            returning=returning+','
        else:
            returning=returning+'},'
    returning=returning+typestr+'},'
    
    return returning
    

def str_type(type):
    #switch type from API value to equivalent used by Splunk GCP Add-On for compatability
    switcher={
                'bool_value:':'"boolValue"',
                'int64_value:':'"int64Value"',
                'double_value:':'"doubleValue"',
                'string_value:':'"stringValue"',
                'distribution_value':'"distributionValue"'
              }
    return switcher.get(type,'"TYPE_UNSPECIFIED"')
       
def pullPointsList(in_str):
    #extract the points from the list of values returned by the API call. Return dict with json, _time, and metric value
    #in the case of distribution values, the value is taken from the mean value

    header='"points": [{"interval": {"endTime":'
    
    retarr={}
    count=0

    start_t = in_str.find('seconds:',1) + 8
    while start_t>7:
        end_t = in_str.find('}',start_t)
        strtime=in_str[start_t:end_t]
        nanos_t = strtime.find('nanos')
        if nanos_t>0:
            strtime=strtime[0:nanos_t]  #some points have nanos.
        
        starttime=uxtime(int(strtime))

        start_t2 = in_str.find('seconds:',end_t) + 8
        end_t2 = in_str.find('}',start_t2)
        endtimeNum = in_str[start_t2:end_t2-3] 
        nanos_t = endtimeNum.find('nanos')
        if nanos_t>0:
            endtimeNum=endtimeNum[0:nanos_t]  #some points have nanos.  
        
        endtime=uxtime(int(endtimeNum))
        
        start_vt = in_str.find('value {',start_t) + 10
        end_vt = in_str.find(' ',start_vt)
        valuet = str_type(in_str[start_vt:end_vt])

        if valuet=='"distributionValue"':
            end_val = in_str.find('}\n}',end_vt) 
            
            value='{' + getDistribution(in_str[end_vt+5:end_val-5])
            retarr[count,0]=header + '"' + endtime+'",'+' "startTime": "' + starttime + '"},"value": {' + valuet + ':' + value + '}}}]'
            mean_st=value.find('"mean":')+7
            if mean_st<7:                   #some distributions return with empty datasets; we will ignore those later
                value='-'
            else:
                mean_end=value.find(',',mean_st)-1
                value=value[mean_st:mean_end]
        else:
            end_val = in_str.find('}',end_vt) -1
            value = in_str[end_vt+1:end_val]                  
            if value=='':
                value='0'
            retarr[count,0]=header + '"' + endtime+'",'+' "startTime": "' + starttime + '"},"value": {'
            retarr[count,0]=retarr[count,0] + valuet + ': "' + value + '"}}]'
        
        retarr[count,1]= endtimeNum
        retarr[count,2]= value
        count=count+1
        start_t = in_str.find('seconds:',end_val) + 8
        #end while
        
    return retarr

def get_metric_kind(in_str):
    #pull out the metric Kind details, return in json format
    start_kind=in_str.find('metric_kind')+13
    end_kind=in_str.find('\n',start_kind)
    metricKind='"metricKind": "' + in_str[start_kind:end_kind] + '",'
    return metricKind

def get_value_type(in_str):
    #pull out the value type and return in json format 
    start_type=in_str.find('value_type')+12
    end_type=in_str.find('\n',start_type)
    valueType='"valueType": "' + in_str[start_type:end_type] + '"'
    return valueType
    
def getDistribution(in_str):
    #for distribution values, need to re-format the payload into a json format compatible with the Splunk GCP Add-On

    in_str=in_str.replace('count:','"count":')
    in_str=in_str.replace(' mean:',',"mean":')
    in_str=in_str.replace(' sum_of_squared_deviation:',',"sumOfSquaredDeviation":')
    in_str=in_str.replace(' bucket_options ',',"bucketOptions":')
    in_str=in_str.replace('exponential_buckets','"exponentialBuckets":')
    in_str=in_str.replace('num_finite_buckets:','"numFiniteBuckets":')
    in_str=in_str.replace(' growth_factor:',',"growthFactor":')
    in_str=in_str.replace(' scale',',"scale"')

    first_bucket=in_str.find('bucket_counts')-1
    if first_bucket>0:
        buckets=in_str[first_bucket:]
        buckets=buckets.replace('bucket_counts:', '')
        bucketvals=re.sub("(\d)",r'"\1",',buckets)
        in_str=in_str[0:first_bucket-1]+', "bucketCounts":['+bucketvals+']'
        in_str=re.sub(",\s*]",']',in_str)        #replace the last comma
        in_str=in_str.replace(' ','')

    return in_str


class HECThreadWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the log from the queue
            logdata = self.queue.get()
            try:
                splunkHec(logdata)
            finally:
                self.queue.task_done()


def splunkHec(logdata):
  #post to HEC
  url = 'https://'+os.environ['HEC_URL']
  try:
    ix_type=os.environ['METRIC_INDEX_TYPE']
  except:
    ix_type='EVENT'

  if ix_type=='EVENT':
    url=url+'/services/collector/event'
  else:
    url=url+'/services/collector'
  token = os.environ['HEC_TOKEN']
  s = requests.Session()
  #s.config['keep_alive'] = False        #HEC performance is improved by keepalive, but event distribution is affected. Setting to false provides better event distribution across indexers
  s.mount( 'http://' , HTTPAdapter(max_retries= 3 )) 
  s.mount( 'https://' , HTTPAdapter(max_retries= 3 ))
  
  authHeader = {'Authorization': 'Splunk '+ token}
  
  try:
    r = s.post(url, headers=authHeader, data=logdata, verify=False, timeout=2)
    r.raise_for_status()
  except requests.exceptions.HTTPError as errh:
    print ("Http Error:",errh)
    print(errh.response.status_code)
    if errh.response.status_code<500:
        print(r.json())
    errorHandler(logdata,url,token)
  except requests.exceptions.ConnectionError as errc:
    print ("Error Connecting:",errc)
    errorHandler(logdata,url,token)
  except requests.exceptions.Timeout as errt:
    print ("Timeout Error:",errt)
    errorHandler(logdata,url,token)
  except requests.exceptions.RequestException as err:
    print ("Error: ",err)
    errorHandler(logdata,url,token)
  except:
    print("unknown Error in http post >> message content:")
    print(logdata.replace('\n',''))
    errorHandler(logdata,url,token)
    



def errorHandler(logdata,url,token):
    """Publishes failed messages to RETRY Pub/Sub topic."""

    from google.cloud import pubsub_v1

    project_id = os.environ['PROJECTID']
    topic_name = os.environ['RETRY_TOPIC']
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    
    data = logdata.encode('utf-8')
    future = publisher.publish(topic_path, data, url=url, token=token, source='MetricsFunction')
    print(future.result())
    print('Published messages into PubSub')
