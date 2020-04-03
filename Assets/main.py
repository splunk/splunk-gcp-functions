# Assets0.5
# Called from PubSub Topic
# Create CRON schedule to send a PubSub to call the Function to refresh the asset inventory
# Use GCS function template to read from GCS into HEC

import os
import time

def hello_pubsub(event, context):
    
    parent_id = os.environ['PARENT']
    
    dump_file_path = os.environ['GCS_FILE_PATH']
    now = time.time()
    export_assets(parent_id, dump_file_path+str(now))

    
def export_assets(id, dump_file_path):
   
    from google.cloud import asset_v1
    from google.cloud.asset_v1.proto import asset_service_pb2

    client = asset_v1.AssetServiceClient()
    output_config = asset_service_pb2.OutputConfig()
    output_config.gcs_destination.uri = dump_file_path
    response = client.export_assets(id, output_config, content_type='RESOURCE')
       