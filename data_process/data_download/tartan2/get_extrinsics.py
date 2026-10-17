import rospy
import tf
import numpy as np
np.set_printoptions(60)
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common_math import create_transformation_matrix

def print_transform():
    rospy.init_node('tf_listener')

    listener = tf.TransformListener()

    trans, rot = None, None
    i = 0 
    while not rospy.is_shutdown():
        try:
            (trans, rot) = listener.lookupTransform('multisense/left_camera_optical_frame', 'vehicle', rospy.Time(0))
            rospy.signal_shutdown("Condition met, shutting down")

        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            continue
    
    print("Written method")
    trans_mat = create_transformation_matrix(rot, trans)
    print(trans_mat)

def tartan_transform():

    vehicle_to_multi_head = create_transformation_matrix([-0.0119,  0.1131,  0.0003,  0.9935], [-0.0949,  0.0641, -0.136])
    multi_head_to_optical = create_transformation_matrix([-0.500, 0.500, -0.500, 0.500], [0.005, 0.105, 0.000])

    trans_mat =  vehicle_to_multi_head @ multi_head_to_optical
    print(trans_mat)


    
if __name__ == '__main__':
    print_transform()