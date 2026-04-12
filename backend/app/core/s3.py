from typing import Annotated
import boto3
from fastapi import Depends
from app.core.config import config
from botocore.client import Config
from types_boto3_s3.client import S3Client as ActualS3Client

AWS_BUCKET = config.s3_bucket_name

def get_s3_client():
    s3_client = boto3.client(            
        "s3",
        endpoint_url=config.s3_url,
        aws_access_key_id=config.s3_login,
        aws_secret_access_key=config.s3_password,
        config=Config(signature_version="s3v4")
    )
    try:
        yield s3_client
    finally:
        s3_client.close()

    
S3Client = Annotated[ActualS3Client, Depends(get_s3_client)]