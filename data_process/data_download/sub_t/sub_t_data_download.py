# from onedrivedownloader import download
import argparse
import os
import yaml
import requests

def download_file(url, local_filename):
    """
    Downloads a file from a given URL and saves it locally.
    """
    try:
        # Send a GET request to the URL in binary format
        with requests.get(url, stream=True) as r:
            r.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=10485760):
                    f.write(chunk)
        print(f"File '{local_filename}' downloaded successfully.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

def main(args : argparse):

    base_path = args.base_path
    
    with open(args.yaml_filepath) as s:
        yaml_file = yaml.safe_load(s)

    url = yaml_file['url']
    save_dir_names = yaml_file['directory']
    save_file_names = yaml_file['filename']

    for link, dir_name, file_name in zip(url, save_dir_names, save_file_names):

        save_filepath = os.path.join(base_path, dir_name)

        if not os.path.exists(save_filepath):
            os.makedirs(save_filepath)

        save_filename = os.path.join(save_filepath, file_name)

        download_file(link, save_filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--base_path', type=str, default=None, required=True, help='parent directory where you\'ll store all files')

    parser.add_argument("--yaml_filepath", type=str, default=None, required=True, help="yaml filepath")
    
    args = parser.parse_args()

    main(args)

