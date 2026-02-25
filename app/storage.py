import os
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "cip-images")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")


def get_s3_client():
    kwargs = {"region_name": AWS_REGION}

    if S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = S3_ENDPOINT_URL
        kwargs["aws_access_key_id"] = os.getenv("AWS_ACCESS_KEY_ID")
        kwargs["aws_secret_access_key"] = os.getenv("AWS_SECRET_ACCESS_KEY")

    return boto3.client("s3", **kwargs)


def ensure_bucket_exists():
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
    except ClientError:
        # LocalStack (and many AWS setups) are fine with a simple create_bucket
        s3.create_bucket(Bucket=S3_BUCKET)


def put_bytes(*, key: str, data: bytes, content_type: str):
    ensure_bucket_exists()
    s3 = get_s3_client()
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )