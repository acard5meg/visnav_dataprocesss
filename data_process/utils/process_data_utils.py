#!/usr/bin/env python
import numpy as np
import io
from PIL import Image
import cv2
from typing import Any, Tuple, List, Dict, Union

from utils.odom_6_dof import *
from utils.rosbag_compat import Bag

def process_images(im_list: List, img_process_func) -> List:
    """
    Process image data from a topic that publishes ros images 
    into a list of PIL images
    """
    images = []
    for img_msg in im_list:
        img = img_process_func(img_msg)
        images.append(img)

    return images

def process_tartan_img(msg) -> Image:
    """
    Process image data from a topic that publishes sensor_msgs/Image 
    to a PIL image for the tartan_drive dataset
    """
    img = ros_to_numpy(msg)
    img = img.astype(np.uint8)
    # reverse the axis order to get the image in the right orientation
    img = np.moveaxis(img, 0, -1)
    # convert rgb to bgr
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    img = Image.fromarray(img)

    return img

def process_subt_tunnel_img(msg) -> Image:
    '''
    Don't love this function since it hard code the camera resolution
    '''
    img = ros_to_numpy_jpeg_comp(msg, output_resolution=(1024, 544))
    img = img.astype(np.uint8)
    
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    img = Image.fromarray(img)

    return img

def process_rellis_3d_img(msg) -> Image:
    '''
    Process data from Rellis 3d image topic which is encoded as bayer_rggb8
    '''
    img = ros_to_numpy_bayer(msg)
    
    img = np.moveaxis(img, 0, -1)
    img = Image.fromarray(img)

    return img

def process_scand_img(msg) -> Image:
    """
    Process image data from a topic that publishes sensor_msgs/CompressedImage
     to a PIL image for the scand dataset
    """
    # convert sensor_msgs/CompressedImage to PIL image
    img = Image.open(io.BytesIO(msg.data))

    w, h = img.size

    return img

def process_odom(
    odom_list: List,
    odom_process_func: Any,
    rotation_matrix : np.ndarray

) -> Dict[np.ndarray, np.ndarray]:
    """
    Process odom data from a topic that publishes nav_msgs/Odometry into 
    position (x,y,z) and roll, pitch, yaw
    """
    xyzs = []
    rpys = []
    for odom_msg in odom_list:
        xyz, rpy = odom_process_func(odom_msg)
        xyzs.append(xyz)
        rpys.append(rpy)
    deltas = calculate_delta_poses(xyzs, rpys, rotation_matrix)
    return {"position": np.array(xyzs), "rotations": np.array(rpys), "deltas": deltas}

def calculate_delta_poses(
    xyz : List[float], 
    rpy : List[float],
    rotation_matrix : np.ndarray
) -> np.ndarray:
    '''
    Calculates change in poses for all poses in trajectory
    Convert everything to conventional axis frames before calculating deltas
    '''
    new_xyz = convert_standard_odom_frame(xyz, rotation_matrix)

    new_xyz = new_xyz.tolist()

    delta_poses = []

    for idx in range(1, len(new_xyz)):
        
        pos1 = np.array([new_xyz[idx-1], rpy[idx-1]], dtype=np.float64)
        pos2 = np.array([new_xyz[idx], rpy[idx]], dtype=np.float64)
            
        calc_delta = to_robot_np(pos1,pos2).flatten().tolist()
            
        # use pos1 (previous position) as robot frame and convert pos2 (new position)
        # to pos1 frame to determine the change in position and rotation
        delta_poses.append(calc_delta)

    return np.array(delta_poses)

def nav_to_xyz_rpy(
    odom_msg
) -> Tuple[List[float], List[float]]:
    """
    Process odom data from a topic that publishes nav_msgs/Odometry into 6DOF position
    """
    p = odom_msg.pose.pose.position
    xyz = [p.x, p.y, p.z]

    o = odom_msg.pose.pose.orientation
    rpy = quaternion_to_angle([o.x, o.y, o.z, o.w])

    return xyz, rpy

def transform_odom_to_camera(
    pose,
    rotation_matrix : np.ndarray
) -> List[float]:
    '''
    pose: is pose from odometry message in base link frame
    rotation_matrix: trnasformation from base frame to camera frame
    '''
    if hasattr(pose, 'x') and hasattr(pose, 'y') and hasattr(pose, 'z'):
        odom_frame_pose = np.array([pose.x, pose.y, pose.z, 1.], dtype=np.float64).reshape(4,1)
    elif isinstance(pose, list):
        odom_frame_pose = np.array([pose[0], pose[1], pose[2], 1.], dtype=np.float64).reshape(4,1)
    elif isinstance(pose, np.ndarray):
        odom_frame_pose = np.concatenate((pose, np.array([1.]))).reshape(4,1)

    camera_frame_pose = rotation_matrix @ odom_frame_pose

    cam_pos = camera_frame_pose[:3].flatten().tolist()

    return cam_pos

def get_images_and_odom(
    bag: Bag,
    imtopics: Union[List[str], str],
    odomtopics: Union[List[str], str],
    img_process_func: Any,
    odom_process_func: Any,
    rotation_matrix : np.ndarray,
    rate: float = 4.0
):
    """
    Get image and odom data from a bag file

    Args:
        bag (Bag): bag file
        imtopics (list[str] or str): topic name(s) for image data
        odomtopics (list[str] or str): topic name(s) for odom data
        img_process_func (Any): function to process image data
        odom_process_func (Any): function to process odom data
        rate (float, optional): rate to sample data. Defaults to 4.0.
        ang_offset (float, optional): angle offset to add to odom data. Defaults to 0.0.
        rotation_matrix (4x4 numpy array): transformation from base link to camera frame
    Returns:
        img_data (list): list of PIL images
        traj_data (dictionary): dictionary with keys postion, rotation, deltas
    """
    # check if bag has both topics
    odomtopic = None
    imtopic = None

    if type(imtopics) == str:
        imtopic = imtopics
    else:
        for imt in imtopics:
            if bag.get_message_count(imt) > 0:
                imtopic = imt
                break
    if type(odomtopics) == str:
        odomtopic = odomtopics
    else:
        for ot in odomtopics:
            if bag.get_message_count(ot) > 0:
                odomtopic = ot
                break

    if not (imtopic and odomtopic):
        # bag doesn't have both topics
        return None, None

    synced_imdata = []
    synced_odomdata = []
    # get start time of bag in seconds
    currtime = bag.get_start_time()

    curr_imdata = None
    curr_odomdata = None

    for topic, msg, t in bag.read_messages(topics=[imtopic, odomtopic]):
        if topic == imtopic:
            curr_imdata = msg
        elif topic == odomtopic:
            curr_odomdata = msg
        if (t.to_sec() - currtime) >= 1.0 / rate:
            if curr_imdata is not None and curr_odomdata is not None:
                synced_imdata.append(curr_imdata)
                synced_odomdata.append(curr_odomdata)
                currtime = t.to_sec()

    img_data = process_images(synced_imdata, img_process_func)

    traj_data = process_odom(
        synced_odomdata,
        odom_process_func,
        rotation_matrix=rotation_matrix
    )
    
    return img_data, traj_data


def anymal_bag_sync(
    odom_bag : Bag,
    image_bag : Bag,
    imtopics: str,
    odomtopics: str,
    img_process_func: Any,
    odom_process_func: Any,
    rotation_matrix : np.ndarray,
    rate: float = 4.0
):
    # the values come back as list of tuples (time, msg)
    # sorted by time
    odometry_msgs = get_bag_msg(odom_bag, odomtopics)
    image_msgs =  get_bag_msg(image_bag, imtopics)
    start_time = min(odometry_msgs[0][0], image_msgs[0][0])

    synced_odomdata, synced_imdata = [], []
    # we know the odometry is faster than the image data 
    # so it will be the outer loop
    curr_img_idx = 0
    currtime = image_msgs[curr_img_idx][0]
    for t, msg in odometry_msgs:
        
        if (t - currtime) >= 1.0 / rate:
            synced_odomdata.append(msg)
            synced_imdata.append(image_msgs[curr_img_idx][1])
            curr_img_idx += 1
            if curr_img_idx >= len(image_msgs):
                break
            currtime = image_msgs[curr_img_idx][0]

    img_data = process_images(synced_imdata, img_process_func)

    traj_data = process_odom(
        synced_odomdata,
        odom_process_func,
        rotation_matrix=rotation_matrix
    )
    
    return img_data, traj_data


def get_bag_msg(
    bag : Bag,
    topic : str
):
    messages = []

    for topic, msg, t in bag.read_messages(topics=[topic]):
        messages.append((t.to_time(), msg))

    messages.sort()

    return messages

def convert_standard_odom_frame(
    xyz : Union[List[float], np.ndarray],
    rotation_matrix: np.ndarray
) -> np.ndarray:
    '''
    Converts the xyz position to be standard coordinate frame x forward, y left, z up
    Needed for proper calculation of distances moved

    Returns converted xyz coordinates in array shape (trajectory length, 3)
    '''
    if isinstance(xyz, list):
        xyz = np.array(xyz)
        
    converted_xyz = np.zeros((len(xyz), 4))
    converted_xyz[:, :3] = xyz
    converted_xyz.resize((len(xyz), 4, 1))

    batch_rotation_matrix = np.zeros((converted_xyz.shape[0], 4, 4))
    batch_rotation_matrix[:, ] = rotation_matrix

    conv_xyz = batch_rotation_matrix @ converted_xyz

    new_xyz = conv_xyz[:, :3, 0]

    return new_xyz

# cut out non-positive velocity segments of the trajectory
def filter_backwards(
    img_list: List[Image.Image],
    traj_data: Dict[str, np.ndarray],
    rotation_matrix : np.ndarray,
    start_slack: int = 0,
    end_slack: int = 0,
) -> Tuple[List[np.ndarray], List[int]]:
    """
    Cut out non-positive velocity segments of the trajectory
    Args:
        img_list: list of images
        traj_data: dictionary of position and yaw data
        start_slack: number of points to ignore at the start of the trajectory
        end_slack: number of points to ignore at the end of the trajectory
    Returns:
        cut_trajs: list of cut trajectories
        start_times: list of start times of the cut trajectories
    """
    traj_pos = traj_data["position"]
    conv_traj_pos = convert_standard_odom_frame(traj_pos, rotation_matrix)
    traj_rot = traj_data["rotations"]

    cut_trajs = []
    start = True

    def process_pair(traj_pair: list) -> Tuple[List, Dict]:
        
        new_img_list, new_traj_data = zip(*traj_pair)
        new_traj_data = np.array(new_traj_data)
        new_traj_pos = new_traj_data[:, :3]
        conv_new_traj = convert_standard_odom_frame(new_traj_pos, rotation_matrix)
        new_traj_rots = new_traj_data[:, 3:]

        new_deltas = []

        for i in range(1, conv_new_traj.shape[0]):

            pos1 = np.array([conv_new_traj[i-1], new_traj_rots[i-1]])
            pos2 = np.array([conv_new_traj[i], new_traj_rots[i]])

            calc_delta = to_robot_np(pos1,pos2).flatten().tolist()
            
            new_deltas.append(calc_delta)

        new_deltas = np.array(new_deltas)

        return (new_img_list, 
        {"position": new_traj_pos, "rotations": new_traj_rots,
         'deltas':new_deltas})

    for i in range(max(start_slack, 1), len(traj_pos) - end_slack):

        pos1 = np.concatenate((conv_traj_pos[i - 1], traj_rot[i - 1]))
        pos2 = np.concatenate((conv_traj_pos[i], traj_rot[i]))
        
        # use pos1 (previous position) as robot frame and convert pos2 (new position)
        # to pos1 frame to determine if you've moved backwards
        # based on whether x is positive
        deltas = to_robot_np(pos1, pos2).squeeze(0).tolist()

        # THIS GIVES YOU THE CHANGE MOVING FROM I-1 AND I 
        # IF THIS IS POSITIVE KEEP THE I-1 IMAGE AND THE CORRESPONDING DELTA  
        
        if deltas[0] > 0:
            if start:
                new_traj_pairs = [
                    
                    (img_list[i - 1], 
                    [*traj_pos[i - 1],
                    *traj_rot[i - 1]
                     ])
                ]
                start = False
            elif i == len(traj_pos) - end_slack - 1:
                cut_trajs.append(process_pair(new_traj_pairs))
            else:
                new_traj_pairs.append(
                    
                    (img_list[i - 1], 
                    [*traj_pos[i - 1],
                    *traj_rot[i - 1]

                     ])

                )

        elif not start:
            cut_trajs.append(process_pair(new_traj_pairs))
            start = True

    return cut_trajs

def ros_to_numpy(
    msg, nchannels=3, empty_value=None, output_resolution=None, aggregate="none"
):
    """
    Convert a ROS image message to a numpy array
    """
    
    if output_resolution is None:
        output_resolution = (msg.width, msg.height)

    try:
        is_rgb = "8" in msg.encoding
    except AttributeError:
        is_rgb = "8" in msg.format

    if is_rgb:
        data = np.frombuffer(msg.data, dtype=np.uint8).copy()
    else:
        data = np.frombuffer(msg.data, dtype=np.float32).copy()

    data = data.reshape(msg.height, msg.width, nchannels)

    if empty_value:
        mask = np.isclose(abs(data), empty_value)
        fill_value = np.percentile(data[~mask], 99)
        data[mask] = fill_value

    data = cv2.resize(
        data,
        dsize=(output_resolution[0], output_resolution[1]),
        interpolation=cv2.INTER_AREA,
    )

    if aggregate == "littleendian":
        data = sum([data[:, :, i] * (256**i) for i in range(nchannels)])
    elif aggregate == "bigendian":
        data = sum([data[:, :, -(i + 1)] * (256**i) for i in range(nchannels)])

    if len(data.shape) == 2:
        data = np.expand_dims(data, axis=0)
    else:
        data = np.moveaxis(data, 2, 0)  # Switch to channels-first

    return data

def ros_to_numpy_jpeg_comp(
    msg, nchannels=3, empty_value=None, output_resolution=None, aggregate="none"
):
    """
    Convert a compressed ROS image message to a numpy array
    """
    if output_resolution is None:
        output_resolution = (msg.width, msg.height)

    try:
        is_rgb = "8" in msg.encoding
    except AttributeError:
        is_rgb = max("8" in msg.format, "jpeg" in msg.format)

    if is_rgb:
        data = np.frombuffer(msg.data, dtype=np.uint8).copy()
    else:
        data = np.frombuffer(msg.data, dtype=np.float32).copy()

    data = cv2.imdecode(data, cv2.IMREAD_COLOR)

    return data

def ros_to_numpy_bayer(msg,
                    nchannels=3, 
                    empty_value=None, 
                    output_resolution=None,
                    aggregate="none"
    ):
    '''
    Converts ros msg using Bayer encoding to a numpy array
    '''

    if output_resolution is None:
        output_resolution = (msg.width, msg.height)

    is_rgb = "8" in msg.encoding
    
    if is_rgb:
        data = np.frombuffer(msg.data, dtype=np.uint8).copy()
    else:
        data = np.frombuffer(msg.data, dtype=np.float32).copy()

    data = data.reshape(msg.height, msg.width)

    if empty_value:
        mask = np.isclose(abs(data), empty_value)
        fill_value = np.percentile(data[~mask], 99)
        data[mask] = fill_value

    data = cv2.cvtColor(data, cv2.COLOR_BayerRGGB2RGB)

    if aggregate == "littleendian":
        data = sum([data[:, :, i] * (256**i) for i in range(nchannels)])
    elif aggregate == "bigendian":
        data = sum([data[:, :, -(i + 1)] * (256**i) for i in range(nchannels)])

    if len(data.shape) == 2:
        data = np.expand_dims(data, axis=0)
    else:
        data = np.moveaxis(data, 2, 0)  # Switch to channels-first

    return data