import kleinkram
from pathlib import Path
import argparse
import os
import yaml

def main(args: argparse):

    with open(args.yaml_filepath) as y:
        yaml_file = yaml.safe_load(y)

    missions = kleinkram.list_missions(project_names=yaml_file['mission_names'])

    download_folder = yaml_file['download_folder']
    patterns = yaml_file['patterns']

    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    invaild_mission_names = []
    for m in missions:
        files = kleinkram.list_files(mission_ids=[m.id], file_names=patterns)
        if len(files) == 0:
            print(f"No files found for mission {m.name} matching patterns {patterns}")
            invaild_mission_names.append(m.name)
            continue

        child_folder_name = m.metadata['Short Name'].value

        full_download_path = os.path.join(download_folder, child_folder_name)

        if not os.path.exists(full_download_path):
            os.makedirs(full_download_path)
        # breakpoint()
        kleinkram.download(
            file_ids=[f.id for f in files],
            dest=full_download_path,
            verbose=True,
            overwrite=True
        )

    print(f"Failed mission names: {invaild_mission_names}")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--yaml_filepath", type=str, default=None, required=True, help="yaml filepath")
    
    args = parser.parse_args()

    main(args)