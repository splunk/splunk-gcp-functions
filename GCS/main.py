#GCSfunction v0.1.3

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

import logging
import os
from google.cloud import storage
#import time
#import json
#from datetime import datetime
#from datetime import date
#import time

import base64
import argparse
import pprint
import re
import requests
from requests.adapters import HTTPAdapter
import urllib3
##turns off the warning that is generated below because using self signed ssl cert
urllib3.disable_warnings()



def hello_gcs(event, context):
    """Triggered by a change to a Cloud Storage bucket.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    file = event
    print(f"Processing file: {file['name']}.")
    read_file(file)

    
def read_file(file):
    # batch size balance between time to create http connection vs distribution of events across indexers
    batch=8000  #characters/bytes per batch
    storage_client = storage.Client()
    
    objectname=file['bucket']+'/'+file['name']
    bucket = storage_client.get_bucket(file['bucket'])
    blob = bucket.blob(file['name'])
    try:
      contents = blob.download_as_string().decode("utf-8")
    except:
      #exception happens when partial uploads/file not complete. Drop out of the function gracefully
      print('not sent to Splunk - incomplete upload')
      return
    startpt = 0
    lastpt = batch
    message_count=0
    message_content=''
    content_length = len(contents)
    
    if content_length>batch:
        try:
          linebrk=os.environ['LINE_BREAKER']
        except:
          linebrk='\n'
        try:
          before=os.environ['BEFORE']    #non-mandatory env variable. Default is to break after
          if (before!='TRUE') or (before!='FALSE'): #validate - default to after if not TRUE or FALSE
            before='FALSE'
        except:
          before='FALSE'
        
        while lastpt<=content_length:
            pos=re.search(linebrk,contents[lastpt:])
            if before=='TRUE':
              splunkHec(contents[startpt:pos.start()+lastpt], objectname)
              startpt=pos.start()+lastpt+1
            else:
              splunkHec(contents[startpt:pos.end()+lastpt], objectname)
              startpt=pos.end()+lastpt+1

            lastpt=startpt+batch

    if lastpt>content_length:
        splunkHec(contents[startpt:],objectname)


def splunkHec(logdata, objectname):
  url = 'https://'+os.environ['HEC_URL']+'/services/collector/raw'
  token = os.environ['HEC_TOKEN']
  s = requests.Session() 
  s.mount( 'http://' , HTTPAdapter(max_retries= 3 )) 
  s.mount( 'https://' , HTTPAdapter(max_retries= 3 ))
  
  authHeader = {'Authorization': 'Splunk '+ token}
 
  try:
    r = s.post(url, headers=authHeader, data=logdata.encode("utf-8"), verify=False, timeout=1)
    r.raise_for_status()
  except requests.exceptions.HTTPError as errh:
    print ("Http Error:",errh)
    if errh.response.status_code<500:
        print(r.json())
    errorHandler(logdata,objectname,url,token)
  except requests.exceptions.ConnectionError as errc:
    print ("Error Connecting:",errc)
    errorHandler(logdata,objectname,url,token)
  except requests.exceptions.Timeout as errt:
    print ("Timeout Error:",errt)
    errorHandler(logdata,objectname,url,token)
  except requests.exceptions.RequestException as err:
    print ("Error: ",err)
    errorHandler(logdata,objectname,url,token)
  except:
    print("unknown Error in http post >> message content:")
    print(logdata.replace('\n',''))
    errorHandler(logdata,objectname,url,token)

 
    
    
def errorHandler(logdata,source,url,token):
    """Publishes failed messages to Pub/Sub topic to Retry later."""

    from google.cloud import pubsub_v1


    project_id = os.environ['PROJECTID']
    topic_name = os.environ['RETRY_TOPIC']
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    
    data = logdata.encode('utf-8')
    # Add two attributes, origin and username, to the message
    future = publisher.publish(topic_path, data, url=url, token=token, origin=source, source='gcpSplunkGCSFunction')
    