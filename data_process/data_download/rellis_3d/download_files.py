import gdown
import os
import os.path
import argparse
import yaml
import sys

# url = 'https://drive.google.com/uc?id=1TRJOnqbTQaHUxUNJ9oAt3MsK-T7UlkIX'
# output = '/home/robotixx/world_model_nav/datasets/rellis_3d/test.tgz'
# gdown.download(url, output, quiet=False)

class GoogleDriveDownloader:
    def __init__(self, yaml_file, output):
        self.url = "https://drive.google.com/uc?id="
        self.config = self.load_yaml(yaml_file)

    def load_yaml(self, file):
        if not os.path.isfile(file):
            sys.exit(f"{file} is not a file. Exiting")
        with open(file, "r") as f:
            return yaml.load(f, Loader=yaml.FullLoader)

    def download_data(self, bag_file, output):

        gdown.download(''.join([self.url, bag_file]), output, quiet=False)

def main(args: argparse.Namespace):
    gdd = GoogleDriveDownloader(args.input_yaml, args.output_dir)

    for dataset_name in gdd.config['datasets']:
        
        curr_dir = os.path.join(args.output_dir, dataset_name)

        if not os.path.exists(curr_dir):
            os.makedirs(curr_dir)

        
        for bag_files in gdd.config['datasets'][dataset_name]:
            
            url_tag = gdd.config['datasets'][dataset_name][bag_files]
            
            gdd.download_data(url_tag, os.path.join(curr_dir, bag_files))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-yaml",
        "-i",
        type=str,
        help="path of the yaml file with datasets",
        required=True,
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        help="path for processed dataset",
        required=True
    )

    args = parser.parse_args()
    main(args)

