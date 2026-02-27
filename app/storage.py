import os
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urlparse, urlunparse

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "cip-images")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")

S3_PUBLIC_BASE_URL = os.getenv("S3_PUBLIC_BASE_URL")

# default 1 hr presigned urls
PRESIGN_EXPIRES_IN = int(os.getenv("PRESIGN_EXPIRES_IN", "3600"))

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

def _rewrite_presigned_url(url: str) -> str:
    """
    generate_presigned_url() uses the boto3 client endpoint host (localstack).
    need localhost instead.
    """
    if not S3_PUBLIC_BASE_URL:
        return url

    parsed = urlparse(url)
    public = urlparse(S3_PUBLIC_BASE_URL)

    return urlunparse(
        (
            public.scheme or parsed.scheme,
            public.netloc or parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def presign_get_url(*, key: str, expires_in: int | None = None) -> str | None:
    """
    returns a presigned url for GETing an obj
    if presigning fails, return None
    """
    ensure_bucket_exists()
    s3 = get_s3_client()
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in or PRESIGN_EXPIRES_IN,
        )
        return _rewrite_presigned_url(url)
    except ClientError:
        return None
    
def delete_object(*, key: str) -> None:
    # for DELETE, later
    ensure_bucket_exists()
    s3 = get_s3_client()
    s3.delete_object(Bucket=S3_BUCKET, Key=key)