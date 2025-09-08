import csv
import json
import os
import shutil
from pathlib import Path
import boto3
from concurrent.futures import ThreadPoolExecutor

# -----------------------------
# Function to read metadata definition from JSON file
# -----------------------------
def read_metadata_definition(metadata_file):
    with open(metadata_file, 'r') as f:
        metadata_definition = json.load(f)
    return metadata_definition

# -----------------------------
# Function to process CSV file and generate row-level files
# -----------------------------
def process_csv(input_csv, metadata_definition, outputs_dir):
    embedding_attributes = metadata_definition['csv']['embeddingAttributes']
    metadata_attributes = metadata_definition['csv']['metadataAttributes']
    index_id_attributes = metadata_definition['csv']['index_id']

    # Create or clean outputs folder within data folder
    if os.path.exists(outputs_dir):
        shutil.rmtree(outputs_dir)
    os.makedirs(outputs_dir)

    with open(input_csv, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            # Generate index_id based on attributes provided
            index_id_values = [row[attr] for attr in index_id_attributes]
            # Clean index ID: replace spaces and slashes
            index_id = '_'.join([v.replace(' ', '_').replace('/', '-') for v in index_id_values])

            # Process embedding attributes
            embedding_data = {attr: row[attr] for attr in embedding_attributes}
            embedding_output_path = os.path.join(outputs_dir, f'{index_id}.csv')
            with open(embedding_output_path, 'w', newline='', encoding='utf-8') as embedding_csv:
                csv_writer = csv.DictWriter(embedding_csv, fieldnames=embedding_attributes)
                csv_writer.writeheader()
                csv_writer.writerow(embedding_data)

            # Process metadata attributes
            metadata_data = {attr: row[attr] for attr in metadata_attributes}
            metadata_output_path = f'{embedding_output_path}.metadata.json'
            with open(metadata_output_path, 'w', encoding='utf-8') as metadata_json:
                json.dump({'metadataAttributes': metadata_data}, metadata_json, indent=4)

# -----------------------------
# Function to upload a single file to S3
# -----------------------------
def upload_file(bucket_name, local_path, s3_path):
    s3_client = boto3.client('s3')
    s3_client.upload_file(local_path, bucket_name, s3_path)
    print(f'Uploaded {local_path} to s3://{bucket_name}/{s3_path}')

# -----------------------------
# Function to upload all files in a directory to S3 using threads
# -----------------------------
def upload_files_to_s3(bucket_name, local_directory, s3_prefix=''):
    with ThreadPoolExecutor(max_workers=20) as executor: 
        futures = []
        for root, dirs, files in os.walk(local_directory):
            for file in files:
                local_path = os.path.join(root, file)
                s3_path = os.path.join(s3_prefix, os.path.relpath(local_path, local_directory)).replace('\\','/')
                futures.append(executor.submit(upload_file, bucket_name, local_path, s3_path))
        
        for future in futures:
            future.result()

# -----------------------------
# Main function
# -----------------------------
def main():
    project_root = Path(__file__).parent.parent

    # Update these paths for your project
    input_csv = project_root / 'data' / '2324_combined.csv'
    metadata_file = project_root / 'data' / '2324_combined.metadata.json'
    local_directory = project_root / 'data' / 'outputs'
    bucket_name = 'utilities-hackathon-2025'

    # Read metadata definition
    metadata_definition = read_metadata_definition(metadata_file)
    print("Metadata definition loaded:", metadata_definition)

    # Process CSV into row-level files
    print("Processing CSV into row-level files...")
    process_csv(input_csv, metadata_definition, local_directory)

    # Upload all files to S3
    print(f"Uploading all row-level files to s3://{bucket_name}/outputs/")
    upload_files_to_s3(bucket_name, local_directory, s3_prefix='outputs')

    print("Done! All files uploaded successfully.")

# -----------------------------
if __name__ == '__main__':
    main()
