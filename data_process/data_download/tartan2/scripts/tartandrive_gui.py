# NEEDS TO BE RUN WITH conda activate fwm_conda
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


with open("./assets/files.yaml") as stream:
    FILE_MAP = yaml.safe_load(stream)


KITTI_FILE_MAP = FILE_MAP['kitti']

# Function to get the metadata from the YAML file
def get_metadata(bucket_name, directory):
    try:
        metadata_obj = minio_client.get_object(bucket_name, f"bags/{directory}/info.yaml")
        metadata = yaml.safe_load(metadata_obj)
        metadata_obj.release_conn()
        return metadata.get('duration'), metadata.get('top_speed')
    except S3Error as e:
        messagebox.showerror("Error", f"Could not retrieve metadata: {e}")
        return None, None

# Function to list directories in the bucket
def list_directories(bucket_name):
    directories = []
    try:
        for obj in KITTI_FILE_MAP:
            if obj != 'files':
                directories.append(obj.split('/')[-2])
    except S3Error as e:
        messagebox.showerror("Error", f"Could not list directories: {e}")
    return directories

def list_items(bucket_name, prefix):
    items = []
    try:
        for obj in KITTI_FILE_MAP[prefix]:
            if obj == 'files':
                for sub_obj in KITTI_FILE_MAP[prefix]['files']:
                    items.append(sub_obj)
            else:
                items.append(obj)
    except S3Error as e:
        messagebox.showerror("Error", f"Could not list directories: {e}")
    return items

# Function to download selected directory
def download_directory(bucket_name, directory, save_path, type):

    if '.' in directory.split('/')[-1]:  #probably a file

        minio_client.fget_object(bucket_name, directory, save_path)
    else: # directory, for now assuming only one level of depth
        if type == 'bags':

            if directory + '/' in FILE_MAP[type]:
                i_bags = tqdm(FILE_MAP[type][directory + '/']['files'])
                for file in i_bags:
                    i_bags.set_description("Downloading " + file)
                    f_save_path = save_path + '/' + file.split('/')[-1]
                    minio_client.fget_object(bucket_name, file, f_save_path)
                    # print("Saving " + file + " to " + f_save_path)
        else:
            for file in FILE_MAP[type]['/'.join(directory.split('/')[:-2]) + '/'][directory]['files']:
                f_save_path = save_path + file.split('/')[-1]
                minio_client.fget_object(bucket_name, file, f_save_path)


def add_option(option_name):
    if option_name not in kitti_vars:
        var = tk.IntVar()
        kitti_vars[option_name] = var
        disp_name = option_name.split('/')
        if len(disp_name[-1]) == 0:
            disp_name = disp_name[-2]
        else:
            disp_name = disp_name[-1].split('.')[0]
        chk = tk.Checkbutton(modalities_frame, text=disp_name, variable=var)
        chk.pack(anchor=tk.W)
        modalities_frame.window_create('end', window=chk)
        modalities_frame.insert('end','\n')
        option_widgets.append(chk)

def remove_options():

    global modalities_frame
    modalities_frame.pack_forget()
    modalities_frame.destroy()
    modalities_frame = ScrolledText(root)
    modalities_frame.pack()
    kitti_options_frame.pack(fill=tk.BOTH, expand=1)
    kitti_vars.clear()

# Function to handle directory selection and hover
def on_select(event):
    w = event.widget
    if len(w.curselection()) == 0:
        #probably clicking something else, not sure how this hook works
        return
    index = int(w.curselection()[0])
    directory = w.get(index)
    duration, top_speed = get_metadata(bucket_name, directory)
    hover_text.set(f"Duration: {duration}, Top Speed: {top_speed}")

    on_radio_select()

    display_image_and_plot(directory)

def repopulate_checkboxes(directory):
    remove_options()
    items = list_items(bucket_name, 'kitti/all_topics/' + directory + '/')
    for item in items:
        add_option(item)

# Function to display image and plot points
def display_image_and_plot(directory):
    try:
        plt.clf()
        points_obj = minio_client.get_object(bucket_name, f"bags/{directory}/gps.npy")
        points_path = os.path.join("temp_pts.npy")
        with open(points_path, 'wb') as f:
            for data in points_obj.stream(32*1024):
                f.write(data)
        points_obj.release_conn()
        t_odom = np.load(points_path)

        try:
            row,col = _dat.index(-t_odom[:,1], t_odom[:,0])
        except:
            row, col = rowcol(_dat.transform, -t_odom[:,1], t_odom[:,0])
        row = np.array(row).astype(float)
        col = np.array(col).astype(float)
        row *= _scale
        col *= _scale
        bad_thresh = -726698.0 * _scale
        if np.any(np.array(col) < bad_thresh + 50):
            row = row[col >= bad_thresh + 50]
            col = col[col >= bad_thresh + 50]

        fig = Figure()
        p1 = fig.add_subplot(111)
        plt.figure(figsize=(4, 4))

        p1.imshow(np.transpose(_map,(1,2,0)))

        p1.plot(col, row,'-r')
        p1.axis('off')
        fig.tight_layout()

        if hasattr(display_image_and_plot, 'canvas'):
            display_image_and_plot.canvas.get_tk_widget().pack_forget()
            display_image_and_plot.canvas.get_tk_widget().destroy()
        display_image_and_plot.canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        display_image_and_plot.canvas.draw()
        display_image_and_plot.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add toolbar
        if hasattr(display_image_and_plot, 'toolbar'):
            display_image_and_plot.toolbar.pack_forget()
            display_image_and_plot.toolbar.destroy()
        display_image_and_plot.toolbar = NavigationToolbar2Tk(display_image_and_plot.canvas, plot_frame)
        display_image_and_plot.toolbar.update()
        display_image_and_plot.toolbar.pack(fill=tk.BOTH, expand=True)

    except S3Error as e:
        messagebox.showerror("Error", f"Could not retrieve image or points: {e}")

# Function to handle download button click
def download_selected_directory():
    selected_dir = directory_listbox.get(directory_listbox.curselection())
    save_path = filedialog.askdirectory()
    if save_path:
        if dataset_type.get() == 'kitti':
            selected_options = [option for option, var in kitti_vars.items() if var.get() == 1]
            i_selected_options = tqdm(selected_options)
            for option in i_selected_options:
                i_selected_options.set_description("Downloading modality: " + option)
                option_path = option
                splits = option.split('/')
                if len(splits[-1]) == 0:
                    suffix = '/'.join(splits[-3:])
                else:
                    suffix = '/'.join(splits[-2:])
                save_path_final = os.path.join(save_path, suffix)
                download_directory(bucket_name, option_path, save_path_final, 'kitti')
        else:
            download_directory(bucket_name, 'bags/'+selected_dir, os.path.join(save_path, selected_dir),'bags')


def on_radio_select():
    if dataset_type.get() == 'kitti':
        try:
            cur_dir = directory_listbox.get(directory_listbox.curselection())
            repopulate_checkboxes(cur_dir)
        except:
            messagebox.showerror("Error", "Please make sure a directory is selected")

    else:
        kitti_options_frame.pack_forget()
        global modalities_frame
        modalities_frame.pack_forget()
        modalities_frame.destroy()

# Function to select/deselect all checkboxes
def select_all():
    for var in kitti_vars.values():
        var.set(1)

# Function to deselect all checkboxes
def deselect_all():
    for var in kitti_vars.values():
        var.set(0)

access_key = "nFNreHkFY2ca56vIHVaU"
secret_key = "IHnkXfe30TjJxkVpF8LuP8wQ7kWoMRrb5QpwcK7Z"
endpoint_url = "airlab-share-02.andrew.cmu.edu:9000"

# Minio client configuration
minio_client = Minio(endpoint_url, access_key=access_key, secret_key=secret_key,secure=True, cert_check=False)

# Bucket name
bucket_name = 'tartandrive2'

def download_wo_gui():
    # suppresses Insecure request warning
    import urllib3
    urllib3.disable_warnings()

    for d in list_directories(bucket_name):
        
        download_directory(bucket_name, os.path.join('bags', d), '/home/robotixx/world_model_nav/datasets/tartan_2/' + d, 'bags')
        

if __name__ == "__main__":
    download_wo_gui()
