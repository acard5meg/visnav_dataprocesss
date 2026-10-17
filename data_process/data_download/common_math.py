import math
import numpy as np
from typing import Iterable

def euler_from_quaternions(x: float, y: float, z: float, w: float):
    t0 = 2.0 * (w * x + y * z)
    t1 = 1.0 - 2.0 * (x * x + y * y)
    roll_x = math.atan2(t0, t1)

    t2 = 2.0 * (w * y - z * x)
    t2 = max(min(t2, 1.0), -1.0)
    pitch_y = math.asin(t2)

    t3 = 2.0 * (w * z + x * y)
    t4 = 1.0 - 2.0 * (y * y + z * z)
    yaw_z = math.atan2(t3, t4)
    return roll_x, pitch_y, yaw_z

def quaternion_to_angle(q: Iterable[float]):
    qx, qy, qz, qw = q
    return np.asarray(euler_from_quaternions(qx, qy, qz, qw), dtype=np.float64)

def euler_to_rotation_matrix(euler_angles):
    r, p, y = np.asarray(euler_angles, dtype=np.float64)
    cr, cp, cy = np.cos([r, p, y])
    sr, sp, sy = np.sin([r, p, y])

    R_x = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=np.float64)
    R_y = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=np.float64)
    R_z = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=np.float64)
    return R_z @ R_y @ R_x

def create_transformation_matrix(quaternion, translation):
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = euler_to_rotation_matrix(quaternion_to_angle(quaternion))
    T[:3, 3] = np.asarray(translation, dtype=np.float64)
    return T