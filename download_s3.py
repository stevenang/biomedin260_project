import json
import os
import subprocess
import argparse
import logging


def download_s3_objects(json_file, output_folder):
    """
    Read S3 URIs from JSON file and download files to specified output folder

    :param json_file: Path to the JSON file containing S3 object information
    :param output_folder: Folder where files should be downloaded
    """
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Ensure output folder exists
    if not os.path.exists(output_folder):
        logging.info(f"Creating output folder: {output_folder}")
        os.makedirs(output_folder)

    try:
        # Read JSON file
        with open(json_file, 'r') as f:
            objects = json.load(f)

        logging.info(f"Found {len(objects)} objects in JSON file")

        # Download each object
        for i, obj in enumerate(objects):
            s3_uri = obj.get('s3_uri')
            if not s3_uri:
                logging.warning(f"S3 URI not found for object: {obj}")
                continue

            # Get the filename from the S3 URI
            filename = os.path.basename(s3_uri)
            if not filename:
                # If the key ends with a slash, it's a folder
                logging.info(f"Skipping folder: {s3_uri}")
                continue

            # Construct output path
            output_path = os.path.join(output_folder, filename)

            # Download using AWS CLI
            logging.info(f"Downloading [{i + 1}/{len(objects)}]: {s3_uri} to {output_path}")

            command = ['aws', 's3', 'cp', s3_uri, output_path]
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                logging.info(f"Successfully downloaded: {filename}")
            else:
                logging.error(f"Failed to download {s3_uri}: {result.stderr}")

        logging.info(f"Download process completed")

    except FileNotFoundError:
        logging.error(f"JSON file not found: {json_file}")
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format in file: {json_file}")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Download S3 objects from JSON file')
    parser.add_argument('--json', default='./data/s3_objects.json',
                        help='Path to JSON file with S3 object information (default: data/s3_objects.json)')
    parser.add_argument('--output', default='./anat',
                        help='Output folder for downloaded files (default: downloads)')

    args = parser.parse_args()

    # Run the download process
    download_s3_objects(args.json, args.output)