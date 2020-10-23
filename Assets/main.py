# Assets 1.0
# Called from PubSub Topic
# Create CRON schedule to send a PubSub to call the Function to refresh the asset inventory
# Use GCS function template to read from GCS into HEC

import os
import time

def hello_pubsub(event, context):
    
    from google.cloud import asset_v1
    
    parent_id = os.environ['PARENT']
    
    dump_file_path = os.environ['GCS_FILE_PATH']
    now = time.time()

    client = asset_v1.AssetServiceClient()
    output_config = asset_v1.OutputConfig()
    output_config.gcs_destination.uri = dump_file_path+str(now)
    content_type = asset_v1.ContentType.RESOURCE

    response = client.export_assets(
        request={
            "parent": parent_id,
            "content_type": content_type,
            "output_config": output_config
            }
    )