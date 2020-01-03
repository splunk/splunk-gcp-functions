#GCP - PubSubFunction v0.1.10

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

from datetime import datetime
from datetime import date

import time
import requests
from requests.adapters import HTTPAdapter
import urllib3
##turns off the warning that is generated below because using self signed ssl cert
urllib3.disable_warnings()


def hello_pubsub(event, context):
    
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    now_time = round(time.time(),3)
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')

    timestamp_srt=pubsub_message.find(',"timestamp":"')+14
    timestamp_end=len(pubsub_message)-2
    timestamp=pubsub_message[timestamp_srt:timestamp_end]

    try:
      host=os.environ['HOST']
    except:
      host='GCPFunction'
    try:
      sourcetype=os.environ['SPLUNK_SOURCETYPE']
    except:
      sourcetype='google:gcp:pubsub:message'
    try:
      source=os.environ['SPLUNK_SOURCE']
    except:
      source=context.resource.get("name")
    try:
        indexing=os.environ['INDEX']
    except:
        indexing='False'
    
    indexname=''

    if indexing!='False':
      if indexing=='LOGNAME':
        #find the position of the logname
        st=pubsub_message.find('"logName":"') 
        #make sure logname is in the event
        if st>0:
            #find end of the logname
            end=pubsub_message.find('",',st)
            #find the tail end of the standard lognames
            st_log=pubsub_message.find('%2F',st,end)
            if st_log==-1:
                #wasn't a standard logname, use all logname
                st_log=pubsub_message.find('/logs/',st,end)
                #final check if logname exists
                if st_log>0:
                    #a logname is found, get the logname
                    logname=pubsub_message[st_log+6:end]
                else:
                    logname='NULL'
            else:
                #get the logname after %2F
                logname=pubsub_message[st_log+3:end]
            print(logname)
            if logname!='NULL':
                try:
                    indexname=os.environ[logname]   #get the index name from the environment variable
                except:
                    indexname=''                    #variable not set, so default to empty string - use the token default index, or index set in another env variable       
            else:
                indexname=indexing                    #if env variable INDEX is any value other than LOGNAME, then the value here is the index name
 
    if indexname!='':
        indexname='"index":"'+indexname+'",'

    
    source=context.resource['name']
    splunkmessage='{"time":'+str(now_time)+',"host":"'+host+'","source":"'+source+'","sourcetype":"'+sourcetype+'",'+indexname
    str_now_time=uxtime(now_time)

    try:
        COMPATIBLE=os.environ['COMPATIBLE']
    except:
        COMPATIBLE='TRUE'

    if COMPATIBLE=='TRUE':
        payload='{"publish_time":'+str(now_time)+', "data":'+pubsub_message+', "attributes": {"logging.googleapis.com/timestamp":"'+timestamp+'"}}'
    else:
        #over-ride to allow raw payload through without original Splunk GCP Add-on wrapper
        payload=pubsub_message

    splunkmessage=splunkmessage+'"event":'+payload+'}'
    splunkHec(splunkmessage,source)


    
def splunkHec(logdata,source):
  url = 'https://'+os.environ['HEC_URL']+'/services/collector/event'
  token = os.environ['HEC_TOKEN']
  s = requests.Session() 
  s.mount( 'http://' , HTTPAdapter(max_retries= 3 )) 
  s.mount( 'https://' , HTTPAdapter(max_retries= 3 ))
  
  authHeader = {'Authorization': 'Splunk '+ token}
  
  try:
  
    r = s.post(url, headers=authHeader, data=logdata.encode("utf-8"), verify=False, timeout=2)
    r.raise_for_status()
  except requests.exceptions.HTTPError as errh:
    print ("Http Error:",errh)
    if errh.response.status_code<500:
        print(r.json())
    errorHandler(logdata,source,url,token)
  except requests.exceptions.ConnectionError as errc:
    print ("Error Connecting:",errc)
    errorHandler(logdata,source,url,token)
  except requests.exceptions.Timeout as errt:
    print ("Timeout Error:",errt)
    errorHandler(logdata,source,url,token)
  except requests.exceptions.RequestException as err:
    print ("Error: ",err)
    errorHandler(logdata,source,url,token)
  except:
    print("unknown Error in http post >> message content:")
    print(logdata.replace('\n',''))
    errorHandler(logdata,source,url,token)



def uxtime(unixtime):
    return datetime.utcfromtimestamp(unixtime).strftime('%Y-%m-%d %H:%M:%S')   




def errorHandler(logdata,source,url,token):
    """Publishes failed messages to Pub/Sub topic to Retry later."""

    from google.cloud import pubsub_v1


    project_id = os.environ['PROJECTID']
    topic_name = os.environ['RETRY_TOPIC']
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    
    data = logdata.encode('utf-8')
    # Add url, token and source attributes to the message
    future = publisher.publish(topic_path, data, url=url, token=token, origin=source, source='gcpSplunkPubSubFunction')
   

