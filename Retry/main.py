#RetryAll0.2.1.py
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

import os
import requests
from requests.adapters import HTTPAdapter
import urllib3
import time
import threading
from threading import Thread
from queue import Queue
##turns off the warning that is generated below because using self signed ssl cert
urllib3.disable_warnings()


def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    try:
        TIMEOUT=int(os.environ['TIMEOUT'])-20
    except:
        TIMEOUT=220 #default timeout for pulling from pub-sub. 
        
    startTime = time.time()
    messageCount=1
    spawned=0
    while messageCount!=0:
        try:
            messageCount=synchronous_pull(os.environ['PROJECTID'],os.environ['SUBSCRIPTION'])
        except:
            messageCount=0
        if (time.time()-startTime)>TIMEOUT:
            messageCount=0
        if (messageCount>0) and (spawned==0):
            retrypushHandler()
            spawned=1 #only fire another retry once
            
            

def synchronous_pull(project_id, subscription_name):
    """Pulling messages synchronously."""
    # [START pubsub_subscriber_sync_pull]
    from google.cloud import pubsub_v1

    try:
        NUM_MESSAGES=int(os.environ['BATCH'])
    except:
        NUM_MESSAGES=100 #default pull from pub-sub

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
        
    # The subscriber pulls a specific number of messages.
    response = subscriber.pull(subscription_path, max_messages=NUM_MESSAGES)
    
    ack_ids=AckMessages()
    incount=0
    outcount=0
    
    queue = Queue()
    threadcount=10
    
    if len(response.received_messages)<threadcount:
        threadcount = len(response.received_messages)

    # Create (max) 10 worker threads (no need to thread more than number of messages)
    for x in range(threadcount):
        worker = ThreadWorker(queue)
        # Set as daemon thread 
        worker.daemon = True
        worker.start()

    # Pop the messages into the thread queue 
    for received_message in response.received_messages:
        incount=incount+1 
        tok=received_message.message.attributes["token"]
        url=received_message.message.attributes["url"]
        queue.put((url, tok, received_message, ack_ids))
    # wait for the queue to finish processing all the tasks
    queue.join()    
    
    # Acknowledges the messages that were succesfully written so they will not be sent again.
    if len(ack_ids.ack_ids)>0:
        subscriber.acknowledge(subscription_path, ack_ids.ack_ids)
    outcount=len(ack_ids.ack_ids)

    print('in:'+str(incount)+' success:'+str(outcount))
    return outcount    
     
    

#threadsafe ack list
class AckMessages:
    def __init__(self):
        self.ack_ids = []
        self._lock = threading.Lock()

    def locked_update(self, ack_id):     
        with self._lock:
            self.ack_ids.append(ack_id)  

#thread worker - calls hec function
class ThreadWorker(Thread):

    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the payloads from the queue and expand the queue
            url, token, received_message, ack_ids = self.queue.get()
            try:
                if splunkHec(url,token,received_message.message.data):
                    ack_ids.locked_update(received_message.ack_id)
            finally:
                self.queue.task_done()
                
def splunkHec(url,token,logdata):
    #check for empty log
    if len(logdata)==0:
        return True
    #test for over-rides. All 3 over-ride variables must be available to over-ride.
    try:
        url_o = 'https://'+os.environ['HEC_URL']+'/services/collector'
    except:
        url_o = 'x'
    try:
        token_o = os.environ['HEC_TOKEN']
    except:
        token_o = 'x'
    try:
        index_type=os.environ['EVENT_TYPE']
    except:
        index_type='x'

    if (url_o!='x' and token_o!='x' and index_type!='x'):
        token=token_o
        if index_type=='METRIC':
            url = 'https://'+os.environ['HEC_URL']+'/services/collector'
        elif index_type=='EVENT':
            url = 'https://'+os.environ['HEC_URL']+'/services/collector/event'
        else:
            url = 'https://'+os.environ['HEC_URL']+'/services/collector/raw'

    s = requests.Session() 
    s.mount( 'http://' , HTTPAdapter(max_retries= 3 )) 
    s.mount( 'https://' , HTTPAdapter(max_retries= 3 ))

    authHeader = {'Authorization': 'Splunk '+ token}

    try:
        r = s.post(url, headers=authHeader, data=logdata, verify=False, timeout=2)
        r.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        print ("Http Error:",errh)
        if errh.response.status_code<500:
            print(r.json())
        return False
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
        return False
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)
        return False
    except requests.exceptions.RequestException as err:
        print ("Error: ",err)
        return False
    return True
        

def retrypushHandler():
    """Publishes a message to Pub/Sub topic to fire another Retry"""

    from google.cloud import pubsub_v1
    
    print('spawning another handler')
    project_id = os.environ['PROJECTID']
    topic_name = os.environ['RETRY_TRIGGER_TOPIC']
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    future = publisher.publish(topic_path, 'SelfSpawn'.encode("utf-8"))