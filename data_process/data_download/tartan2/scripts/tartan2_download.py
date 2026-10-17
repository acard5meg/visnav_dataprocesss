import tkinter as tk
from tkinter import messagebox, filedialog
from minio import Minio
from minio.error import S3Error
import yaml
import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import rasterio
from rasterio.enums import Resampling
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from tkinter.scrolledtext import ScrolledText
from tqdm import tqdm
from rasterio.transform import rowcol
import argparse

# Function to list directories in the bucket
def list_directories(bucket_name, KITTI_FILE_MAP):
    # breakpoint()
    directories = []
    try:
        for obj in KITTI_FILE_MAP:
            if obj != 'files':
                directories.append(obj.split('/')[-2])
    except S3Error as e:
        messagebox.showerror("Error", f"Could not list directories: {e}")
    return directories


# Function to download selected directory
def download_directory(bucket_name, directory, save_path, file_type, KITTI_FILE_MAP, minio_client):
    
    if '.' in directory.split('/')[-1]:  #probably a file
    
        minio_client.fget_object(bucket_name, directory, save_path)
    else: # directory, for now assuming only one level of depth
        if file_type == 'bags':
    
            if directory + '/' in KITTI_FILE_MAP:
    
                i_bags = tqdm(KITTI_FILE_MAP[directory + '/']['files'])
                for file in i_bags:
                    i_bags.set_description("Downloading " + file)
                    f_save_path = save_path + '/' + file.split('/')[-1]
                    minio_client.fget_object(bucket_name, file, f_save_path)
    
        else:
    
            for file in KITTI_FILE_MAP['/'.join(directory.split('/')[:-2]) + '/'][directory]['files']:
                f_save_path = save_path + file.split('/')[-1]
                minio_client.fget_object(bucket_name, file, f_save_path)
    

    

def download_wo_gui(bucket_name, output_filepath, KITTI_FILE_MAP, minio_client):
    # suppresses Insecure request warning
    import urllib3
    urllib3.disable_warnings()

    all_dirs = list_directories(bucket_name, KITTI_FILE_MAP)
    
    for d in all_dirs:
    
        download_directory(bucket_name, os.path.join('bags', d), os.path.join(output_filepath,d), 'bags', KITTI_FILE_MAP, minio_client)
    

def main(args: argparse):
    # get all setup
    with open(args.yaml_filepath) as stream:
        yaml_file = yaml.safe_load(stream)


    with open(yaml_file['download_filepath']) as stream:
        FILE_MAP = yaml.safe_load(stream)

    KITTI_FILE_MAP = FILE_MAP['bags']

    access_key = yaml_file['access_key']
    secret_key = yaml_file['secret_key']
    endpoint_url = yaml_file['endpoint_url']

    # Minio client configuration
    minio_client = Minio(endpoint_url, access_key=access_key, secret_key=secret_key,secure=True, cert_check=False)

    # Bucket name
    bucket_name = yaml_file['bucket_name']

    download_wo_gui(bucket_name, yaml_file['output_filepath'], KITTI_FILE_MAP, minio_client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--yaml_filepath", type=str, default=None, help="yaml filepath")
    
    args = parser.parse_args()

    main(args)

