#GCSfunction v0.2.5

'''MIT License
Copyright (c) 2020 Splunk
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

import threading
from threading import Thread
from queue import Queue

import base64
import argparse
import pprint
import re
import urllib.parse
import requests
from requests.adapters import HTTPAdapter
import urllib3
##turns off the warning that is generated below because using self signed ssl cert
urllib3.disable_warnings()

objectname=""
source=""
contents=""
positions=[[]]

def hello_gcs(event, context):
    """Triggered by a change to a Cloud Storage bucket.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    file = event
    try:
        exclude=os.environ['EXCLUDE']
    except:
        exclude='!settonotexcludeanything!'
    if re.search(exclude, file['name']) != None :
      print(f"Skipping file: {file['name']}. Object name matched exclusion")
      return

    print(f"Processing file: {file['name']}.")
    read_file(file)

    
def read_file(file):
    # batch size balance between time to create http connection vs distribution of events across indexers (#characters/bytes per batch)
    try:
      batch=os.environ['BATCH']    #non-mandatory env variable. Default is 32000
    except:
      batch=32000
    # number of threads to copy to Splunk HEC - default 128
    try:
      threadcount=os.environ['THREADS']   #non-mandatory env variable. Default is 127
    except:
      threadcount=127

    try:
      linebrk=os.environ['LINE_BREAKER']
    except:
      linebrk='\n'
    try:
      before=os.environ['BEFORE']    #non-mandatory env variable. Default is to break after
      if before not in ['TRUE','FALSE']: #validate - default to after if not TRUE or FALSE
        before='FALSE'
    except:
      before='FALSE' 
    
    global objectname
    global contents
    global positions
    global source
     
    storage_client = storage.Client()
    objectname=file['bucket']+'/'+file['name']
    pos=objectname.find('.tmp_chnk_.')
    if pos>-1:
      source=urllib.parse.quote(objectname[0:pos])
    else:
      source=urllib.parse.quote(objectname)
     
    bucket = storage_client.get_bucket(file['bucket'])
    blob = bucket.get_blob(file['name'])
    
    blobsize = blob.size
    
    maxsize=209715200 #200M chunks (can be tuned - but note that memory limits on CF will limit this)
    
    print(f"Object size: {blobsize}")

    if blobsize>maxsize+1 and not (".tmp_chnk_." in file['name']):
      print('Object size is too big for 1 pass. Splitting into sub-objects (temporary)')
      chunk_s=0
      chunk_e=maxsize
      counter=0
      write_client = storage.Client()
      lastpattern="(?s:.*)"+linebrk
      while chunk_e<blobsize:
      
        contents = blob.download_as_string(start=chunk_s,end=chunk_e).decode("utf-8")
        #find last occuring event break in current chunk, so that split is not breaking an event
        matchLastPos=re.search(lastpattern, contents)
        
        if before=="TRUE":
          #search back a little as this is a break before, otherwise can chop on incomplete event
          last_end_s=matchLastPos.end()-20  
          last_end_e=matchLastPos.end()
          narrow=re.search(linebrk,contents[last_end_s:last_end_e])
          lastchunkpos=narrow.start()+last_end_s-1
        else:
          lastchunkpos=matchLastPos.end()
        
        write_bucket = write_client.get_bucket(file['bucket'])
        write_blob = write_bucket.blob(file['name']+'.tmp_chnk_.'+str(counter))
        write_blob.upload_from_string(contents[0:lastchunkpos])
        counter=counter+1
        chunk_s=chunk_s+lastchunkpos
        chunk_e=chunk_s+maxsize
      if chunk_s<blobsize:
        contents = blob.download_as_string(start=chunk_s,end=blobsize).decode("utf-8")
        write_bucket = write_client.get_bucket(file['bucket'])
        write_blob = write_bucket.blob(file['name']+'.tmp_chnk_.'+str(counter))
        write_blob.upload_from_string(contents)
    else:
      #one file to read....
      try:
        contents = blob.download_as_string().decode("utf-8")
      except:
        #exception happens when partial uploads/file not complete. Drop out of the function gracefully
        print('Info: Nothing sent to Splunk yet - the file in GCS has not completed upload. Will re-execute on full write')
        return
      
      startpt = 0
      counter=0
      lastpt = batch
      content_length = len(contents)
      
      queue = Queue()
      
      workers=int(round(content_length/batch))
      if workers<1:
        workers=1
      if workers<threadcount:
          threadcount=workers
      # Create worker threads (no need to thread more than number of packages)
      for x in range(threadcount):
          worker = HECThreadWorker(queue)
          # Set as daemon thread 
          worker.daemon = True
          worker.start()
      
      endpt=batch
      
      if content_length>batch:         
        #more than one batch        
        while endpt<content_length:
          contentsearch=contents[startpt:endpt]
          #find last occuring event break in current chunk, so that split is not breaking an event
          lastpattern="(?s:.*)"+linebrk
          matchLastPos=re.search(lastpattern, contentsearch)
          if before=="TRUE":
            #search back a little as this is a break before, otherwise can chop on incomplete event
            last_end_s=matchLastPos.end()-20  
            last_end_e=matchLastPos.end()
            narrow=re.search(linebrk,contentsearch[last_end_s:last_end_e])
            lastchunkpos=narrow.start()+last_end_s-1
          else:
            lastchunkpos=matchLastPos.end()

          positions.append([])
          positions[counter].append(startpt)
          positions[counter].append(startpt+lastchunkpos)
          counter=counter+1
          startpt=startpt+lastchunkpos
          endpt=startpt+batch
        
        if startpt<content_length:
            positions.append([])
            positions[counter].append(startpt)
            positions[counter].append(content_length)
            counter=counter+1
      else:
        #only one batch
        positions.append([])
        positions[counter].append(startpt)
        positions[counter].append(content_length)
        counter=counter+1

      x=0
      while x<counter:
        queue.put(x)
        x=x+1
      

      # wait for the queue to finish processing all the tasks
      #print('finished processing')
      queue.join()
      
      contents=""
      contentsearch=""
      objectname=""
      source=""
      positions.clear()

      if (".tmp_chnk_." in file['name']):
        print(f"Deleting temporary chunked object: {file['name']}")
        try:
          blob.delete()
        except:
          print("Delete failed")



class HECThreadWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the details from the queue
            logpos = self.queue.get()
            try:
                splunkHec(logpos)
            finally:
                self.queue.task_done()


def splunkHec(logpos):
  global source

  url = 'https://'+os.environ['HEC_URL']+'/services/collector/raw?source=' + source
  try:
    host=os.environ['HOST']
    url=url+'&host='+host
  except:
    host=''
  token = os.environ['HEC_TOKEN']
  s = requests.Session() 
  #s.mount( 'http://' , HTTPAdapter(max_retries= 1 )) 
  s.mount( 'https://' , HTTPAdapter(max_retries= 1 ))
  
  authHeader = {'Authorization': 'Splunk '+ token}
  #print('sending logs to HEC')
  global positions
  pos0 = positions[logpos][0]
  pos1 = positions[logpos][1]
  
  logdata=contents[pos0:pos1]
 
  try:
    r = s.post(url, headers=authHeader, data=logdata.encode("utf-8"), verify=False, timeout=10, stream=False)
    r.raise_for_status()
    r.close()
    s.close()
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
    # Add url, token and source attributes to the message
    future = publisher.publish(topic_path, data, url=url, token=token, origin=source, source='gcpSplunkGCSFunction')
