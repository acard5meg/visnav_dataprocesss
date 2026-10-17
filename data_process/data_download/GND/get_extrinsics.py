import rospy
import tf
import numpy as np
np.set_printoptions(60)
from pathlib import Path
import sys
from scipy.spatial.transform import Rotation as R

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common_math import create_transformation_matrix

def print_transform():
    rospy.init_node('tf_listener')

    listener = tf.TransformListener()
    trans, rot = None, None
    i = 0 
    while not rospy.is_shutdown():
        try:
            
            (trans, rot) = listener.lookupTransform('zed2_left_camera_optical_frame', 'odom', rospy.Time(0))   
            
            rospy.signal_shutdown("Condition met, shutting down")

        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            continue
    

    quat = np.array([rot[0], rot[1], rot[2], rot[3]])
    r = R.from_quat(quat)
    print("Scipy")
    print(r.as_matrix())
    print()
    
    print("Written method")
    trans_mat = create_transformation_matrix(rot, trans)
    print(trans_mat)
    
if __name__ == '__main__':
    print_transform()