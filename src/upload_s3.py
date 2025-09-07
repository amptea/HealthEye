import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv(".env")

s3 = boto3.client("s3", region_name="us-east-1")

bucket_name = "utilities-hackathon-2025"  # replace with your bucket
file_path = "data/flattened_usage.json"
s3_key = "flattened_usage.json"

s3.upload_file(file_path, bucket_name, s3_key)
print(f"Uploaded {file_path} to s3://{bucket_name}/{s3_key}")
