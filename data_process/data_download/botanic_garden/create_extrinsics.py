import yaml
import os
import numpy as np

class BotanicTag:
    def __init__(self, rows, cols, dt, data):
        self.rows = rows
        self.cols = cols
        self.dt = dt
        self.data = data

    def make_array(self):
        if self.dt == 'd':
            dty = np.double
        arr = np.array(self.data, dtype=dty).reshape((self.rows, self.cols))

        return arr
    
def matrix_constructor(loader, node):
    values = loader.construct_mapping(node)
    return BotanicTag(values['rows'], values['cols'], values['dt'], values['data'])


def main():
    yaml.add_constructor(u'tag:yaml.org,2002:opencv-matrix', matrix_constructor)
    cwd = os.getcwd()

    with open(os.path.join(cwd, "calib_chain.yaml"), "r") as f:
        # breakpoint()
        config = yaml.load(f, Loader=yaml.FullLoader)

    T_xsens_rgb0 = config['T_xsens_rgb0'].make_array()
    T_xsens_robot = config['T_xsens_robot'].make_array()

    rot_matrix = np.linalg.inv(T_xsens_rgb0) @ T_xsens_robot

    print(rot_matrix)

if __name__ == "__main__":
    main()