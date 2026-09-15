import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

def parse_s3_path(path_string):
    """
    Parses an S3 ARN or path string into bucket and prefix.
    Example: 'arn:aws:s3:::mys3/folder/' -> ('mys3', 'folder/')
    Example: 'mys3/folder/' -> ('mys3', 'folder/')
    Example: 'mys3' -> ('mys3', '')
    """
    path = path_string.strip()
    if path.startswith("arn:aws:s3:::"):
        path = path.replace("arn:aws:s3:::", "")
    
    if "/" in path:
        parts = path.split("/", 1)
        bucket = parts[0]
        prefix = parts[1]
        # Ensure prefix ends with / if it exists
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        return bucket, prefix
    else:
        return path, ""

def upload_to_s3(file_content, s3_path, object_name, access_key, secret_key, region):
    """Uploads bytes to S3 and verifies existence."""
    try:
        bucket, prefix = parse_s3_path(s3_path)
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # The full S3 key is the prefix + the object name
        full_key = prefix + object_name
        
        # 1. Perform the upload
        s3.put_object(Bucket=bucket, Key=full_key, Body=file_content)
        
        # 2. Verify the upload by attempting to fetch object metadata
        try:
            s3.head_object(Bucket=bucket, Key=full_key)
            return True, "Upload verified successfully!"
        except ClientError as e:
            return False, f"Upload seemed successful, but verification failed: {str(e)}"
            
    except NoCredentialsError:
        return False, "Credentials not available."
    except PartialCredentialsError:
        return False, "Incomplete credentials provided."
    except Exception as e:
        return False, str(e)
