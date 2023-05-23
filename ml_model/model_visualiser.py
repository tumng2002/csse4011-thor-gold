import time
import threading
import serial
import queue
import re
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d as p3d
import serial
import time
import numpy as np
import tensorflow as tf


data_queue = queue.Queue()

SPINE_BASE = 0
SPINE_MID = 1
NECK = 2
HEAD = 3
SHOULDER_LEFT = 4
ELBOW_LEFT = 5
WRIST_LEFT = 6
SHOULDER_RIGHT = 7
ELBOW_RIGHT = 8
WRIST_RIGHT = 9
HIP_LEFT = 10
KNEE_LEFT = 11
ANKLE_LEFT = 12
FOOT_LEFT = 13
HIP_RIGHT = 14
KNEE_RIGHT = 15
ANKLE_RIGHT = 16
FOOT_RIGHT = 17
SPINE_SHOULDER = 18

bone_list = [[SPINE_BASE, SPINE_MID], 
             [SPINE_MID, SPINE_SHOULDER], 
             [SPINE_SHOULDER, NECK], 
             [NECK, HEAD], 
             [SPINE_SHOULDER, SHOULDER_RIGHT], 
             [SHOULDER_RIGHT, ELBOW_RIGHT], 
             [ELBOW_RIGHT, WRIST_RIGHT], 
             [SPINE_SHOULDER, SHOULDER_LEFT], 
             [SHOULDER_LEFT, ELBOW_LEFT], 
             [ELBOW_LEFT, WRIST_LEFT], 
             [SPINE_BASE, HIP_RIGHT], 
             [HIP_RIGHT, KNEE_RIGHT], 
             [KNEE_RIGHT, ANKLE_RIGHT],
             [ANKLE_RIGHT, FOOT_RIGHT], 
             [SPINE_BASE, HIP_LEFT], 
             [HIP_LEFT, KNEE_LEFT], 
             [KNEE_LEFT, ANKLE_LEFT], 
             [ANKLE_LEFT, FOOT_LEFT]]

def update_skeleton(joints, bones, x, y, z):
    joints._offsets3 = (x, y, z)

    for bone, conn in zip(bones, bone_list):
        bone.set_data([x[conn[0]], x[conn[1]]], [y[conn[0]], y[conn[1]]])
        bone.set_3d_properties([z[conn[0]], z[conn[1]]])


def get_uart_in():
    ser = serial.Serial('/dev/ttyUSB0')
    data = []
    while True:
        line = ser.readline()
        # parse the line
        data.append(line)
        if len(data) == 19:
            data_queue.put(list(data))
            data.clear()

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
        # convert data to x, y, z
        x = [] 
        y = []
        z = []
        update_skeleton(joints, bones, x, y, z)
        plt.pause(0.01)
