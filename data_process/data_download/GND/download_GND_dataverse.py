# https://dataverse.tdl.org/dataset.xhtml?persistentId=doi:10.18738/T8/0PRYRH
import os
import time
from pyDataverse.api import NativeApi, DataAccessApi
from pyDataverse.models import Dataverse
import requests

import argparse

base_url = 'https://dataverse.orc.gmu.edu/'

api = NativeApi(base_url)
data_api = DataAccessApi(base_url)

DOI = "doi:10.13021/ORC2020/JUIW5F" # this is fine
dataset = api.get_dataset(DOI) # errpr

files_list = dataset.json()['data']['latestVersion']['files']
# Function to download a file with retry mechanism and exponential backoff

def download_file(download_url, dir, filename):
    max_retries = 5
    backoff_factor = 1
    for attempt in range(max_retries):
        try:
            with requests.get(download_url, stream=True) as response:
                response.raise_for_status()
                with open(os.path.join(dir, filename), "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"Successfully downloaded: {filename}")
            return
        except requests.RequestException as e:
            wait_time = backoff_factor * (2 ** attempt)
            print(f"Error downloading {filename}: {str(e)}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    print(f"Failed to download {filename} after {max_retries} attempts.")


def main(args : argparse.Namespace):
    download_dir = args.output_directory
    curr_files = {*os.listdir(download_dir)}

    for file in files_list:

        if not args.full_download and len(os.listdir(download_dir)) >= 10:
            exit()

        filename = file["dataFile"]["filename"]
        file_id = file["dataFile"]["id"]
        if 'bag' not in os.path.splitext(filename)[1].lower():
            continue

        print(f"Downloading: File name {filename}, id {file_id}")

        if filename in curr_files:
            print(f"{filename} already downloaded! Continuing!")
        else:
            # Construct the download URL
            download_url = f"{base_url}api/access/datafile/{file_id}"

            download_file(download_url, download_dir, filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-directory",
        "-o",
        type=str,
        help="directory where to download file to",
        default="tartan_drive",
        required=True,
    )
    parser.add_argument(
        "--full-download",
        '-f',
        action='store_true',
        help="if True download all files for cleaning else download subset",
        default=False
    )
    
    args = parser.parse_args()
    
    main(args)