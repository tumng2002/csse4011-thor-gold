import threading
import serial
import struct
import queue
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d as p3d
import numpy as np



data_queue = queue.Queue()
ser = serial.Serial('COM9', 115200)

NOSE = 0
LEFT_SHOULDER = 1
RIGHT_SHOULDER = 2
LEFT_ELBOW = 3
RIGHT_ELBOW = 4
LEFT_WRIST = 5
RIGHT_WRIST = 6
LEFT_HIP = 7
RIGHT_HIP = 8
LEFT_KNEE = 9
RIGHT_KNEE = 10
LEFT_ANKLE = 11
RIGHT_ANKLE = 12
LEFT_HEEL = 13
RIGHT_HEEL = 14

bone_list = [[NOSE, LEFT_SHOULDER], 
             [NOSE, RIGHT_SHOULDER], 
             [RIGHT_SHOULDER, LEFT_SHOULDER], 
             [RIGHT_SHOULDER, RIGHT_ELBOW], 
             [RIGHT_ELBOW, RIGHT_WRIST], 
             [LEFT_SHOULDER, LEFT_ELBOW], 
             [LEFT_ELBOW, LEFT_WRIST], 
             [RIGHT_SHOULDER, RIGHT_HIP], 
             [LEFT_SHOULDER, LEFT_HIP], 
             [LEFT_HIP, RIGHT_HIP], 
             [RIGHT_HIP, RIGHT_KNEE], 
             [RIGHT_KNEE, RIGHT_ANKLE], 
             [RIGHT_ANKLE, RIGHT_HEEL],
             [LEFT_HIP, LEFT_KNEE], 
             [LEFT_KNEE, LEFT_ANKLE], 
             [LEFT_ANKLE, LEFT_HEEL]]

def update_skeleton(ax, x, y, z):
    ax.scatter(x, y, z)

    for conn in bone_list:
        ax.plot([x[conn[0]], x[conn[1]]], [y[conn[0]], y[conn[1]]], zs=[z[conn[0]], z[conn[1]]])

def main():
    initial_skeleton = []
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')

    while True:
        data = ser.readline()
        print(data)
        filtered = data[:-1]
        if len(filtered) != 120:
            continue
        d1 = np.frombuffer(filtered, dtype="float32")
        # print(d1)
        x = d1[:15]
        # y = data[num_floats // 3: 2 * (num_floats // 3)]
        y = np.zeros(15)
        z = d1[15:]
        ax.clear()
        ax.set_title("mmWave Skeleton Model")
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.axes.set_xlim3d(left=-0, right=1) 
        ax.axes.set_ylim3d(bottom=-1, top=1) 
        ax.axes.set_zlim3d(bottom=1, top=0) 
        update_skeleton(ax, x, y, z)
        plt.pause(0.1)

        

if __name__ == "__main__":
    main()