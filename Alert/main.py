#GCP - AlertFunction v0.1.0

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


def hello_world(request):
    """Responds to HTTP request from Alert Webhook.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    now_time = round(time.time(),3)
    
    request_json = request.get_json()
    
    if request_json and 'incident' in request_json:
        incident= request_json['incident']
        name = incident['policy_name']
        if str(incident['ended_at'])=='None':
            incident['ended_at']="None"
            request_json['incident']=incident
            
        payload=str(request_json)
    else:
        print('unknown alert message')
        return

    
    try:
      host=os.environ['HOST']
    except:
      host='GCP_Alert_Function'
    try:
      source=os.environ['SPLUNK_SOURCE']
    except:
      source="Stackdriver Alert:"+name
    try:
      sourcetype=os.environ['SPLUNK_SOURCETYPE']
    except:
      sourcetype='google:gcp:alert'
    try:
        indexname=os.environ['INDEX']
    except:
        indexname=''
    
    
    if indexname!='':
        indexname='"index":"'+indexname+'",'
    
    splunkmessage='{"time":'+str(now_time)+',"host":"'+host+'","source":"'+source+'","sourcetype":"'+sourcetype+'",'+indexname
    
    payload=payload.replace("'",'"')
    splunkmessage=splunkmessage+'"event":'+payload+'}'
    #print('payload is:',splunkmessage)
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





def errorHandler(logdata,source,url,token):
    """Publishes failed messages to Pub/Sub topic to Retry later."""

    from google.cloud import pubsub_v1


    project_id = os.environ['PROJECTID']
    topic_name = os.environ['RETRY_TOPIC']
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    
    data = logdata.encode('utf-8')
    # Add two attributes, origin and username, to the message
    future = publisher.publish(topic_path, data, url=url, token=token, origin=source, source='gcpSplunkAlertFunction')
   

   
