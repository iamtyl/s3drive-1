
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

def upload_to_s3(file_content, bucket, object_name, access_key, secret_key, region):
    """Uploads bytes to S3."""
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        s3.put_object(Bucket=bucket, Key=object_name, Body=file_content)
        return True, "Upload successful!"
    except NoCredentialsError:
        return False, "Credentials not available."
    except PartialCredentialsError:
        return False, "Incomplete credentials provided."
    except Exception as e:
        return False, str(e)
