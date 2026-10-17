
import os
import pickle
from PIL import Image
import io
import argparse
import tqdm
import yaml
from tqdm.contrib.concurrent import process_map

from utils.process_data_utils import *
from utils.rosbag_compat import Bag, ROSBagException

def main(args: argparse.Namespace):

    # load the config file
    with open("config/process_bags_config.yaml", "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    # create output dir if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # iterate recurisively through all the folders and get the path of files with .bag extension in the args.input_dir
    bag_files = []
    for root, dirs, files in os.walk(args.input_dir):
        for file in files:
            # if decompress bag don't want to process compressed version
            if file.endswith("orig.bag"):
                continue
            elif file.endswith(".bag"):
                bag_files.append(os.path.join(root, file))
    if args.num_trajs >= 0:
        bag_files = bag_files[: args.num_trajs]
    
    for bag_path in tqdm.tqdm(bag_files, desc="Bags processed"):
        try:
            b = Bag(bag_path)
        except ROSBagException as e:
            print(e)
            print(f"Error loading {bag_path}. Skipping...")
            continue

        # name is that folders separated by _ and then the last part of the path
        traj_name = "_".join(bag_path.split("/")[-2:])[:-4]

        curr_file = bag_path.split('/')

        rot_mat = f'rotation_matrix'
        speed = f'top_speed'
        type_of_robot = f'robot'
        dist_c = f'distortion_coefficients'
        camera_m = f'camera_matrix'
        image_r = f'image_resolution'
        img_func = f"img_process_func"
        width = f"width"
        

        if args.dataset_name == 'scand':
            specifiers = '_' + curr_file[-1].split('_')[1].lower()
            rot_mat = f'rotation_matrix{specifiers}'
            speed = f'top_speed{specifiers}'
            type_of_robot = f'robot{specifiers}'
            width = f"width{specifiers}"

        if args.dataset_name == 'gnd':
            specifiers = '_' + curr_file[-1].split('_')[0].lower()
            if 'umd' in specifiers: 
                dist_c = f'distortion_coefficients{specifiers}'
                camera_m = f'camera_matrix{specifiers}'
                image_r = f'image_resolution{specifiers}'
                img_func = f"img_process_func{specifiers}"

        

        rotation_matrix = np.array(config[args.dataset_name][rot_mat])
        conv_coord_axis = np.array(config[args.dataset_name]["conv_coord_axis"])

        bag_img_data, bag_traj_data = get_images_and_odom(
            b,
            config[args.dataset_name]["imtopics"],
            config[args.dataset_name]["odomtopics"],
            # treats python string as a function e.g. eval('print(55)') == print(55)
            eval(config[args.dataset_name][img_func]),
            eval(config[args.dataset_name]["odom_process_func"]),
            rotation_matrix = conv_coord_axis,
            rate=args.sample_rate
        )

        # Don't need rosbag, save the memory
        b.close()
        del b

        if bag_img_data is None or bag_traj_data is None:
            print(
                f"{bag_path} did not have the topics we were looking for. Skipping..."
            )
            continue

        to_dump = bag_traj_data

        total_steps = len(bag_traj_data['position'])

        uniq_ids = np.linspace(0, total_steps-1, total_steps, dtype=int) # id
        cam_mat = np.array(config[args.dataset_name][camera_m]) # camera
        distortion_model = config[args.dataset_name]['distortion_model']
        distortion_coeff = np.array(config[args.dataset_name][dist_c])
        to_dump.update({'timestep' : uniq_ids})

        to_dump.update({'scene id' : '-'.join([args.dataset_name,traj_name])})
        to_dump.update({'camera matrix' : cam_mat})
        to_dump.update({'distortion model' : distortion_model})
        to_dump.update({'distortion coeff' : distortion_coeff})
        to_dump.update({'top speed' : float(config[args.dataset_name][speed])})
        to_dump.update({'robot' : str(config[args.dataset_name][type_of_robot])})
        to_dump.update({'dataset' : str(args.dataset_name)})
        to_dump.update({'image resolution': config[args.dataset_name][image_r]})
        to_dump.update({'rotation matrix' : rotation_matrix})
        to_dump.update({'width' : float(config[args.dataset_name][width])})
        to_dump.update({'camera distance projection' : float(config[args.dataset_name]['camera_projection'])})
        to_dump.update({'conventional coordinates' : conv_coord_axis})
        
        traj_folder = os.path.join(args.output_dir, traj_name)
        # make a folder for the traj
        if not os.path.exists(traj_folder):
            os.makedirs(traj_folder)
        with open(os.path.join(traj_folder, "traj_data.pkl"), "wb") as f:
            pickle.dump(to_dump, f)


        del to_dump, bag_traj_data

        # create rgb folder
        rbg_folder = os.path.join(traj_folder, 'rgb')
        os.makedirs(rbg_folder, exist_ok=True)
        # save the image data to disk
        for i, img in enumerate(bag_img_data):
            img.save(os.path.join(rbg_folder, f"{i}.jpg"))

        del bag_img_data


def parse_bag(bag_path):
    '''
    parallelized version of code
    run this with tqdm process_map and thread map
    '''
    try:
        b = Bag(bag_path)
    except ROSBagException as e:
        print(e)
        print(f"Error loading {bag_path}. Skipping...")
        return

    # name is that folders separated by _ and then the last part of the path
    traj_name = "_".join(bag_path.split("/")[-2:])[:-4]

    curr_file = bag_path.split('/')

    rot_mat = f'rotation_matrix'
    speed = f'top_speed'
    type_of_robot = f'robot'
    dist_c = f'distortion_coefficients'
    camera_m = f'camera_matrix'
    image_r = f'image_resolution'
    img_func = f"img_process_func"
    width = f"width"
    

    if args.dataset_name == 'scand':
        specifiers = '_' + curr_file[-1].split('_')[1].lower()
        rot_mat = f'rotation_matrix{specifiers}'
        speed = f'top_speed{specifiers}'
        type_of_robot = f'robot{specifiers}'
        width = f"width{specifiers}"

    if args.dataset_name == 'gnd':
        specifiers = '_' + curr_file[-1].split('_')[0].lower()
        if 'umd' in specifiers: 
            dist_c = f'distortion_coefficients{specifiers}'
            camera_m = f'camera_matrix{specifiers}'
            image_r = f'image_resolution{specifiers}'
            img_func = f"img_process_func{specifiers}"

    

    rotation_matrix = np.array(config[args.dataset_name][rot_mat])
    conv_coord_axis = np.array(config[args.dataset_name]["conv_coord_axis"])

    bag_img_data, bag_traj_data = get_images_and_odom(
        b,
        config[args.dataset_name]["imtopics"],
        config[args.dataset_name]["odomtopics"],
        eval(config[args.dataset_name][img_func]),
        eval(config[args.dataset_name]["odom_process_func"]),
        rotation_matrix = conv_coord_axis,
        rate=args.sample_rate
    )

    # Don't need rosbag, save the memory
    b.close()
    del b

    if bag_img_data is None or bag_traj_data is None:
        print(
            f"{bag_path} did not have the topics we were looking for. Skipping..."
        )
        return

    to_dump = bag_traj_data

    total_steps = len(bag_traj_data['position'])

    uniq_ids = np.linspace(0, total_steps-1, total_steps, dtype=int) # id
    cam_mat = np.array(config[args.dataset_name][camera_m]) # camera
    distortion_model = config[args.dataset_name]['distortion_model']
    distortion_coeff = np.array(config[args.dataset_name][dist_c])
    to_dump.update({'timestep' : uniq_ids})

    to_dump.update({'scene id' : '-'.join([args.dataset_name,traj_name])})
    to_dump.update({'camera matrix' : cam_mat})
    to_dump.update({'distortion model' : distortion_model})
    to_dump.update({'distortion coeff' : distortion_coeff})
    to_dump.update({'top speed' : float(config[args.dataset_name][speed])})
    to_dump.update({'robot' : str(config[args.dataset_name][type_of_robot])})
    to_dump.update({'dataset' : str(args.dataset_name)})
    to_dump.update({'image resolution': config[args.dataset_name][image_r]})
    to_dump.update({'rotation matrix' : rotation_matrix})
    to_dump.update({'width' : float(config[args.dataset_name][width])})
    to_dump.update({'camera distance projection' : float(config[args.dataset_name]['camera_projection'])})
    to_dump.update({'conventional coordinates' : conv_coord_axis})
    
    traj_folder = os.path.join(args.output_dir, traj_name)
    # make a folder for the traj
    if not os.path.exists(traj_folder):
        os.makedirs(traj_folder)
    with open(os.path.join(traj_folder, "traj_data.pkl"), "wb") as f:
        pickle.dump(to_dump, f)

    del to_dump, bag_traj_data

    # create rgb folder
    rbg_folder = os.path.join(traj_folder, 'rgb')
    os.makedirs(rbg_folder, exist_ok=True)
    # save the image data to disk
    for i, img in enumerate(bag_img_data):
        img.save(os.path.join(rbg_folder, f"{i}.jpg"))
            

    del bag_img_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--dataset_name",
        "-d",
        type=str,
        help="name of the dataset (must be in process_config.yaml)",
        default="tartan_drive",
        required=True,
    )
    parser.add_argument(
        "--input_dir",
        "-i",
        type=str,
        help="path of the datasets with rosbags",
        required=True,
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        type=str,
        help="path for processed dataset ",
        required=True,
    )
    # number of trajs to process
    parser.add_argument(
        "--num_trajs",
        "-n",
        default=-1,
        type=int,
        help="number of bags to process (default: -1, all)",
    )
    parser.add_argument(
        "--sample_rate",
        "-s",
        default=10.0,
        type=float,
        help="sampling rate (default: 4.0 hz)",
    )
    parser.add_argument(
        "--parallel",
        action='store_true',
        help="whether to use parallel processing (default: False)",

    )
    # # parallelized version
    global args, configs

    args = parser.parse_args()

    if args.parallel:
        with open("config/process_bags_config.yaml", "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        # create output dir if it doesn't exist
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)

        # iterate recurisively through all the folders and get the path of files with .bag extension in the args.input_dir
        bag_files = []
        for root, dirs, files in os.walk(args.input_dir):
            for file in files:
                # if decompress bag don't want to process compressed version
                if file.endswith("orig.bag"):
                    continue
                elif file.endswith(".bag"):
                    bag_files.append(os.path.join(root, file))
        if args.num_trajs >= 0:
            bag_files = bag_files[: args.num_trajs]

        process_map(parse_bag, bag_files, max_workers=os.cpu_count() - 4)
    else:
        print(f"STARTING PROCESSING {args.dataset_name.upper()} DATASET")
        main(args)
        print(f"FINISHED PROCESSING {args.dataset_name.upper()} DATASET")
