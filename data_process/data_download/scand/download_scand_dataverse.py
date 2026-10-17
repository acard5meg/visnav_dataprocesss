# https://dataverse.tdl.org/dataset.xhtml?persistentId=doi:10.18738/T8/0PRYRH
import argparse
import os
import time
from pathlib import Path

import requests
from pyDataverse.api import NativeApi
from tqdm import tqdm

DOI = "doi:10.18738/T8/0PRYRH"
BASE_URL = "https://dataverse.tdl.org/"
TEST_BAG_LIMIT = 10
CHUNK_SIZE = 8192
MAX_RETRIES = 5
REQUEST_TIMEOUT = 60


def get_files_list(base_url: str, doi: str) -> list[dict]:
    api = NativeApi(base_url)
    dataset = api.get_dataset(doi)
    return dataset.json()["data"]["latestVersion"]["files"]


def is_bag_file(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".bag"


def download_file(download_url: str, output_dir: Path, filename: str) -> bool:
    tmp_path = output_dir / f"{filename}.part"
    final_path = output_dir / filename

    for attempt in range(MAX_RETRIES):
        try:
            with requests.get(
                download_url, stream=True, timeout=REQUEST_TIMEOUT
            ) as response:
                response.raise_for_status()
                total_bytes = int(response.headers.get("Content-Length", 0)) or None
                with open(tmp_path, "wb") as f, tqdm(
                    total=total_bytes,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=filename,
                    leave=True,
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            os.replace(tmp_path, final_path)  # atomic on same filesystem
            print(f"Successfully downloaded: {filename}")
            return True
        except requests.RequestException as e:
            wait_time = 2**attempt
            print(f"Error downloading {filename}: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    print(f"Failed to download {filename} after {MAX_RETRIES} attempts.")
    return False


def main(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    files_list = get_files_list(BASE_URL, DOI)

    existing_bags = {
        p.name for p in output_dir.iterdir() if p.is_file() and is_bag_file(p.name)
    }
    if not args.full_download and len(existing_bags) >= TEST_BAG_LIMIT:
        print(f"Subset already satisfied ({len(existing_bags)} .bag files).")
        return

    for file in files_list:
        filename = file["dataFile"]["filename"]
        if not is_bag_file(filename):
            continue

        if not args.full_download and len(existing_bags) >= TEST_BAG_LIMIT:
            print(f"Reached subset limit ({TEST_BAG_LIMIT} .bag files).")
            break

        if filename in existing_bags:
            print(f"{filename} already downloaded. Skipping.")
            continue

        file_id = file["dataFile"]["id"]
        download_url = f"{BASE_URL}api/access/datafile/{file_id}"
        print(f"Downloading: {filename} (id={file_id})")

        if download_file(download_url, output_dir, filename):
            existing_bags.add(filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-directory",
        "-o",
        type=str,
        help="directory where to download files to",
        default="./scand_dataverse",
        required=True,
    )
    parser.add_argument(
        "--full-download",
        "-f",
        action="store_true",
        help="if set, download all bags; otherwise stop at 10 total .bag files",
        default=False,
    )
    args = parser.parse_args()
    main(args)
