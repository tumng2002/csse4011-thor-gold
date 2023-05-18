import time
import threading
import serial
import queue
import re
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d as p3d

to_database_queue = queue.Queue()

#temp bone list, basically all the points that are joined up together. 
bone_list =  [[1, 3], [2, 3], [3, 4], [4, 7], [5, 7], [6, 7], [1, 8], [2, 9], [8, 10], [9, 11], [10, 12], [11, 13], [5, 14], [6, 15], [14, 16], [15, 17], [16, 18], [17, 19], [3, 20]]


def get_base_data():

    ser = serial.Serial(port="/dev/ttyACM0") # depending on the device used. 
    while True:
        line = ser.readline().decode('utf-8') # assuming still passing through JSON format
        inc_sensor = re.findall('\{(.+?)\}', line)
        if not inc_sensor:
            continue
        for a in inc_sensor:
            data = json.loads("{" + a + "}") 
            to_database_queue.put(data)


def update_skeleton(joints, bones, x, y, z):
    joints._offsets3 = (x, y, z)

    for bone, conn in zip(bones, bone_list):
        bone.set_data([x[conn[0]], x[conn[1]]], [y[conn[0]], y[conn[1]]])
        bone.set_3d_properties([z[conn[0]], z[conn[1]]])

def main():

    data_thread = threading.Thread(target=get_base_data, daemon=True)
    data_thread.start()

    # initial starting point of the model:
    initial_skeleton = []
    fig = plt.figure()
    ax = p3d.Axes3D(fig)

    ax.set_xlim(-2, 2)
    ax.set_xlabel('X')
    ax.set_ylim(0, 4)
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title("mmWave Skeleton Model")

    joints = ax.scatter([],[],[], marker='o', color="green")
    bones = ax.plt([],[],[], linestyle="-", color="green")
    plt.ion()
    
    while True:
        data = to_database_queue.get()

        # COLLECT AND RUN THROUGH MODEL:

        # GET DATA INTO X,Y,Z,
        x = [] 
        y = []
        z = []
        update_skeleton(joints, bones, x, y, z)
        plt.pause(0.1)

        



if __name__ == "__main__":
    main()