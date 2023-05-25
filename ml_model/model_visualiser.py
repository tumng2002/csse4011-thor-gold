import threading
import serial
import struct
import queue
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d as p3d
import numpy as np


data_queue = queue.Queue()

NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28
LEFT_HEEL = 29
RIGHT_HEEL = 30

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

def update_skeleton(joints, bones, x, y, z):
    joints._offsets3 = (x, y, z)

    for bone, conn in zip(bones, bone_list):
        bone.set_data([x[conn[0]], x[conn[1]]], [y[conn[0]], y[conn[1]]])
        bone.set_3d_properties([z[conn[0]], z[conn[1]]])


def get_uart_in():
    ser = serial.Serial('/dev/ttyUSB0', 115200)
    while True:
        line = ser.readline()
        data_queue.put(line)

def main():
    data_thread = threading.Thread(target=get_uart_in, daemon=True)
    data_thread.start()

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
        data = data_queue.get()

        # Define the number of floats in each part of the packet
        num_floats = len(data) // struct.calcsize('f')

        # Convert the packet to a list of floats
        floats = struct.unpack('f' * num_floats, data)

        # Split the list of floats into separate arrays for x, y, and z
        x = floats[:15]
        # y = floats[num_floats // 3: 2 * (num_floats // 3)]
        y = np.zeros(15)
        z = floats[15:]

        update_skeleton(joints, bones, x, y, z)
        plt.pause(0.01)
