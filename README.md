# VISNAV Data Processing

## Overview
This directory provides cleaning scripts to process robotic navigation data into a standardized format.

- `data_process/config`: contains yaml file with all metadata needed during the cleaning process
- `data_process/data_download`: contains bash and/or python scripts to download raw data. Additionally, contains scripts to create various metadata values (e.g. transformation matrices)
- `data_process/data_stats`: contains scripts to create plots, figures, tables, and statistics in the paper
- `data_process/figures`: outputs from `data_stats` scripts
- `data_process/utils`: various helper functions used in the cleaning script
- `process_bags_anymal.py`: processing script used with anymal
- `process_bags.py`: processing script used for all datasets except anymal

## Setup
Script has been run using python 3.10 and 3.12.

1. Create a new python environment `python3 -m venv [environment-name]`
2. Activate environment: `source [environment-name]/bin/activate`
3. Install dependencies: `pip3 -r install requirements.txt`

## Data Processing
See paper website for list of datasets currently processed [VISNAV](https://acard5meg.github.io/VISNAV/)
To run the processing script use the following: `python3 process_bags.py [args]`
Arguments for processing:
1. `--dataset_name`: name of dataset that matches the label in the config.yaml file
2. `--input_dir`: path to directory with data to be cleaned
3. `--output_dir`: path to directory where save cleaned data
4. `--num_trajs`: number of trajectories to process. Defaults to -1 which indicates process all data
5. `--sample_rate`: frequency (Hz) to sample all data to. Defaults to 10Hz. ***NOTE***: If you plan to change this ensure the topics you are processing publish data at least as fast as this number. For our original publication, the slowest camera was 10Hz.

## Config File Guide
The topmost key is the dataset name which matches the value used in the argument parser. ***NOTE***, for any missing values use `XXXXXXXXX`.
1. `odomtopics`: list of comma separated strings denoting the odometry topics to clean. 
2. `imtopics`: list of comma separated strings denoting the image topics to clean.
3. `img_process_func`: name of function in `utils/process_data_utils.py` used to process image topic messages.
4. `odom_process_func`: name of function in `utils/process_data_utils.py` used to process odometry topic messages.
5. `distortion_coefficients`: distortion coefficients for camera used on robot.
6. `distortion_model`: distortion model of camera
7. `camera_matrix`: intrinsic camera matrix
8. `rotation_matrix`: rotation matrix to convert odometry frame to optical frame
9. `conv_coord_axis`: rotation matrix to convert the odometry measurements to standard odometry frame in [ROS REP-103](https://www.ros.org/reps/rep-0103.html)
10. `top_speed`: top speed of robot from manufacturer for action space normalization
11. `angular_velocity`: top angular velocity of robot
12. `image_resolution`: list of integers representing image resolution in pixels denoted [width, height].
13. `robot`: Name of robot used in data collection
14. `width`: Width of robot from manufacturer website. Used in visualization
15. `camera_projection`: Minimum distance required to project odometry measurements onto image in visualization.


### Acknowledgements
Thank you to [General Navigation Models](https://github.com/robodhruv/visualnav-transformer) and [Mohammad Nazeri](https://github.com/mhnazeri/VANP) for open sourcing their code.
