import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

def upload_to_s3(file_content, bucket, object_name, access_key, secret_key, region):
    """Uploads bytes to S3 and verifies existence."""
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # 1. Perform the upload
        s3.put_object(Bucket=bucket, Key=object_name, Body=file_content)
        
        # 2. Verify the upload by attempting to fetch object metadata
        try:
            s3.head_object(Bucket=bucket, Key=object_name)
            return True, "Upload verified successfully!"
        except ClientError as e:
            return False, f"Upload seemed successful, but verification failed: {str(e)}"
            
    except NoCredentialsError:
        return False, "Credentials not available."
    except PartialCredentialsError:
        return False, "Incomplete credentials provided."
    except Exception as e:
        return False, str(e)
