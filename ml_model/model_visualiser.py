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

# def get_uart_in():
#     count = 0
#     while True:
#         line = ser.readline()
        # if (line.decode()[0] != 'E' and line.decode()[0] != 'I'):
#         data_queue.put(line)
#         count += 1

def main():
    # data_thread = threading.Thread(target=get_uart_in, daemon=True)
    # data_thread.start()
    count = 0

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
        plt.pause(0.5)
        # if data == 'E' or data == "I" or data == "[" or data == ' ':
        #     data = ser.readline()
        #     print("LINE: ", data)
        #     continue
        # else:
        #     d = ser.read(119)
        # print(data[:-1])
        # try:
        #     d1 = np.frombuffer(data, dtype="float32")
        #     print(d1)
        #      # Split the list of floats into separate arrays for x, y, and z
        #     x = d1[:15]
        #     # y = data[num_floats // 3: 2 * (num_floats // 3)]
        #     y = np.zeros(15)
        #     z = d1[15:]
        #     ax.clear()
        #     ax.set_title("mmWave Skeleton Model")
        #     ax.set_xlabel('X')
        #     ax.set_ylabel('Y')
        #     ax.set_zlabel('Z')
        #     ax.axes.set_xlim3d(left=-0, right=1) 
        #     ax.axes.set_ylim3d(bottom=-1, top=1) 
        #     ax.axes.set_zlim3d(bottom=1, top=0) 
        #     update_skeleton(ax, x, y, z)
        #     plt.pause(0.5)
        # except ValueError:
        #     continue
        # if count > 50:
        # data = data_queue.get()
        # d1 = b'?\xf5\x96\x01?\xee\x9b\x07?z\xd5\x01?\xb2\x9d\x08>m\x90m>\xe4\xe9k>\x7f\xfb^>\xfcSd>\\\x8cM>\x1aW^>\x06\xd8\xfc>\xd9\xb3\xfe>\x0b\xd2.?MR.?\x16TY?\x01tY?\xd8\xe9]?Bb^?\xed0\x06?<\xb0\x15?\x84"\xeb>\xf5\xf3&?X\xa6\xcb>\xcf\x97??\xe5\x8e\xa8>r\xb8\x0e?\x8c\x17\xf9>\x90\xff\x0c?\xdb\x85\xf8>\x0fu\x0c?3\xb5\x03?\x84\x1a\n'

        # Define the number of floats in each part of the packet
        # num_floats = len(data) // struct.calcsize('f')

        # # # Convert the packet to a list of floats
        # floats = struct.unpack('f' * num_floats, data)
        

        

if __name__ == "__main__":
    main()