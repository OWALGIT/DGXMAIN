import os, boto3
from botocore.config import Config
def client():
    return boto3.client('s3',
        endpoint_url=os.environ['STORJ_ENDPOINT'],
        aws_access_key_id=os.environ['STORJ_KEY'],
        aws_secret_access_key=os.environ['STORJ_SECRET'],
        config=Config(signature_version='s3v4',
                      s3={'addressing_style':'path','payload_signing_enabled':False},
                      retries={'max_attempts':3}))
