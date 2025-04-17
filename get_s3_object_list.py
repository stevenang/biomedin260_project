import boto3
import logging
import json


def get_s3_object_references(bucket_name):
    """
    Generate S3 object references for all objects in a bucket

    :param bucket_name: string - name of the bucket
    :return: Lists of object keys, URLs, and S3 URIs
    """
    # Create a session using your AWS credentials
    s3_resource = boto3.resource('s3')

    try:
        # Get all objects in the bucket
        bucket = s3_resource.Bucket(bucket_name)
        object_info = []

        # Collect information for each object
        for obj in bucket.objects.all():
            region = s3_resource.meta.client.meta.region_name

            # Create both URL and S3 URI formats
            public_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{obj.key}"
            s3_uri = f"s3://{bucket_name}/{obj.key}"
            aws_cli = f"aws s3 cp s3://{bucket_name}/{obj.key} ."

            object_info.append({
                "key": obj.key,
                "url": public_url,
                "s3_uri": s3_uri,
                "aws_cli_download": aws_cli
            })

        return object_info
    except Exception as e:
        logging.error(f"Error accessing bucket: {e}")
        return None


if __name__ == "__main__":
    # Set your bucket name here
    bucket_name = "biomedin260"

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Generate object references
    print(f"Generating S3 references for all objects in bucket: {bucket_name}")
    objects = get_s3_object_references(bucket_name)

    if objects:
        print(f"Found {len(objects)} objects in the bucket")

        # Display object info
        for obj in objects:
            print("\n" + "=" * 50)
            print(f"Object: {obj['key']}")
            print(f"URL: {obj['url']}")
            print(f"S3 URI: {obj['s3_uri']}")
            print(f"AWS CLI Download: {obj['aws_cli_download']}")

        # Save to JSON for programmatic use
        with open('data/s3_objects.json', 'w') as f:
            json.dump(objects, f, indent=2)
        print("\nObject information saved to 's3_objects.json'")

    else:
        print("Failed to access bucket objects. Check your AWS credentials and permissions.")