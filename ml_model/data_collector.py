import time
import threading
import serial
import queue
import struct
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d as p3d
import serial
import time
import numpy as np
import tensorflow as tf
import pandas as pd

# Change the configuration file name
# configFileName = 'AWR1843config.cfg'
configFileName = "tuned-radar.cfg"

CLIport = {}
Dataport = {}
byteBuffer = np.zeros(2**15,dtype = 'uint8')
byteBufferLength = 0




# ------------------------------------------------------------------

# Function to configure the serial ports and send the data from
# the configuration file to the radar
def serialConfig(configFileName):
    
    global CLIport
    global Dataport
    # Open the serial ports for the configuration and the data ports
    
    # Raspberry pi
    #CLIport = serial.Serial('/dev/ttyACM0', 115200)
    #Dataport = serial.Serial('/dev/ttyACM1', 921600)
    
    # Windows - change for whatever device is being used.
    CLIport = serial.Serial('COM12', 115200)
    Dataport = serial.Serial('COM11', 921600)

    # Read the configuration file and send it to the board
    config = [line.rstrip('\r\n') for line in open(configFileName)]
    for i in config:
        CLIport.write((i+'\n').encode())
        print(i)
        time.sleep(0.01)
        
    return CLIport, Dataport

# ------------------------------------------------------------------

# Function to parse the data inside the configuration file
def parseConfigFile(configFileName):
    configParameters = {} # Initialize an empty dictionary to store the configuration parameters
    
    # Read the configuration file and send it to the board
    config = [line.rstrip('\r\n') for line in open(configFileName)]
    for i in config:
        
        # Split the line
        splitWords = i.split(" ")
        
        # Hard code the number of antennas, change if other configuration is used
        numRxAnt = 4
        numTxAnt = 3
        
        # Get the information about the profile configuration
        if "profileCfg" in splitWords[0]:
            startFreq = int(float(splitWords[2]))
            idleTime = int(splitWords[3])
            rampEndTime = float(splitWords[5])
            freqSlopeConst = float(splitWords[8])
            numAdcSamples = int(splitWords[10])
            numAdcSamplesRoundTo2 = 1;
            
            while numAdcSamples > numAdcSamplesRoundTo2:
                numAdcSamplesRoundTo2 = numAdcSamplesRoundTo2 * 2;
                
            digOutSampleRate = int(splitWords[11]);
            
        # Get the information about the frame configuration    
        elif "frameCfg" in splitWords[0]:
            
            chirpStartIdx = int(splitWords[1]);
            chirpEndIdx = int(splitWords[2]);
            numLoops = int(splitWords[3]);
            numFrames = int(splitWords[4]);
            framePeriodicity = float(splitWords[5]);

            
    # Combine the read data to obtain the configuration parameters           
    numChirpsPerFrame = (chirpEndIdx - chirpStartIdx + 1) * numLoops
    configParameters["numDopplerBins"] = numChirpsPerFrame / numTxAnt
    configParameters["numRangeBins"] = numAdcSamplesRoundTo2
    configParameters["rangeResolutionMeters"] = (3e8 * digOutSampleRate * 1e3) / (2 * freqSlopeConst * 1e12 * numAdcSamples)
    configParameters["rangeIdxToMeters"] = (3e8 * digOutSampleRate * 1e3) / (2 * freqSlopeConst * 1e12 * configParameters["numRangeBins"])
    configParameters["dopplerResolutionMps"] = 3e8 / (2 * startFreq * 1e9 * (idleTime + rampEndTime) * 1e-6 * configParameters["numDopplerBins"] * numTxAnt)
    configParameters["maxRange"] = (300 * 0.9 * digOutSampleRate)/(2 * freqSlopeConst * 1e3)
    configParameters["maxVelocity"] = 3e8 / (4 * startFreq * 1e9 * (idleTime + rampEndTime) * 1e-6 * numTxAnt)
    
    return configParameters
   
# ------------------------------------------------------------------
configParameters = parseConfigFile(configFileName)

# Funtion to read and parse the incoming data
def readAndParseData18xx(Dataport, configParameters):
    global byteBuffer, byteBufferLength
    
    # Constants
    OBJ_STRUCT_SIZE_BYTES = 12;
    BYTE_VEC_ACC_MAX_SIZE = 2**15;
    MMWDEMO_UART_MSG_DETECTED_POINTS = 1;
    MMWDEMO_UART_MSG_RANGE_PROFILE   = 2;
    maxBufferSize = 2**15;
    tlvHeaderLengthInBytes = 8;
    pointLengthInBytes = 16;
    magicWord = [2, 1, 4, 3, 6, 5, 8, 7]
    
    # Initialize variables
    magicOK = 0 # Checks if magic number has been read
    dataOK = 0 # Checks if the data has been read correctly
    frameNumber = 0
    detObj = {}
    
    readBuffer = Dataport.read(Dataport.in_waiting)
    byteVec = np.frombuffer(readBuffer, dtype = 'uint8')
    byteCount = len(byteVec)
    
    # Check that the buffer is not full, and then add the data to the buffer
    if (byteBufferLength + byteCount) < maxBufferSize:
        byteBuffer[byteBufferLength:byteBufferLength + byteCount] = byteVec[:byteCount]
        byteBufferLength = byteBufferLength + byteCount
        
    # Check that the buffer has some data
    if byteBufferLength > 16:
        
        # Check for all possible locations of the magic word
        possibleLocs = np.where(byteBuffer == magicWord[0])[0]

        # Confirm that is the beginning of the magic word and store the index in startIdx
        startIdx = []
        for loc in possibleLocs:
            check = byteBuffer[loc:loc+8]
            if np.all(check == magicWord):
                startIdx.append(loc)
               
        # Check that startIdx is not empty
        if startIdx:
            
            # Remove the data before the first start index
            if startIdx[0] > 0 and startIdx[0] < byteBufferLength:
                byteBuffer[:byteBufferLength-startIdx[0]] = byteBuffer[startIdx[0]:byteBufferLength]
                byteBuffer[byteBufferLength-startIdx[0]:] = np.zeros(len(byteBuffer[byteBufferLength-startIdx[0]:]),dtype = 'uint8')
                byteBufferLength = byteBufferLength - startIdx[0]
                
            # Check that there have no errors with the byte buffer length
            if byteBufferLength < 0:
                byteBufferLength = 0
                
            # word array to convert 4 bytes to a 32 bit number
            word = [1, 2**8, 2**16, 2**24]
            
            # Read the total packet length
            totalPacketLen = np.matmul(byteBuffer[12:12+4],word)
            
            # Check that all the packet has been read
            if (byteBufferLength >= totalPacketLen) and (byteBufferLength != 0):
                magicOK = 1
    
    # If magicOK is equal to 1 then process the message
    if magicOK:
        # word array to convert 4 bytes to a 32 bit number
        word = [1, 2**8, 2**16, 2**24]
        
        # Initialize the pointer index
        idX = 0
        
        # Read the header
        magicNumber = byteBuffer[idX:idX+8]
        idX += 8
        version = format(np.matmul(byteBuffer[idX:idX+4],word),'x')
        idX += 4
        totalPacketLen = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        platform = format(np.matmul(byteBuffer[idX:idX+4],word),'x')
        idX += 4
        frameNumber = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        timeCpuCycles = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        numDetectedObj = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        numTLVs = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4
        subFrameNumber = np.matmul(byteBuffer[idX:idX+4],word)
        idX += 4

        # Read the TLV messages
        for tlvIdx in range(numTLVs):
            
            # word array to convert 4 bytes to a 32 bit number
            word = [1, 2**8, 2**16, 2**24]

            # Check the header of the TLV message
            tlv_type = np.matmul(byteBuffer[idX:idX+4],word)
            idX += 4
            tlv_length = np.matmul(byteBuffer[idX:idX+4],word)
            idX += 4

            # Read the data depending on the TLV message
            if tlv_type == MMWDEMO_UART_MSG_DETECTED_POINTS:

                # Initialize the arrays
                x = np.zeros(numDetectedObj,dtype=np.float32)
                y = np.zeros(numDetectedObj,dtype=np.float32)
                z = np.zeros(numDetectedObj,dtype=np.float32)
                velocity = np.zeros(numDetectedObj,dtype=np.float32)
                intensity = np.zeros(numDetectedObj,dtype=np.float32)
                
                for objectNum in range(numDetectedObj):
                    
                    # Read the data for each object
                    x[objectNum] = byteBuffer[idX:idX + 4].view(dtype=np.float32)
                    idX += 4
                    y[objectNum] = byteBuffer[idX:idX + 4].view(dtype=np.float32)
                    idX += 4
                    z[objectNum] = byteBuffer[idX:idX + 4].view(dtype=np.float32)
                    idX += 4
                    velocity[objectNum] = byteBuffer[idX:idX + 4].view(dtype=np.float32)
                    idX += 4
                    intensity[objectNum] = byteBuffer[idX:idX + 4].view(dtype=np.float32)
                    idX += 4
                
                # Store the data in the detObj dictionary
                detObj = {"numObj": numDetectedObj, "x": x, "y": y, "z": z, "velocity":velocity, "intensity":intensity}
                dataOK = 1
                
        # Remove already processed data
        if idX > 0 and byteBufferLength>idX:
            shiftSize = totalPacketLen
            
                
            byteBuffer[:byteBufferLength - shiftSize] = byteBuffer[shiftSize:byteBufferLength]
            byteBuffer[byteBufferLength - shiftSize:] = np.zeros(len(byteBuffer[byteBufferLength - shiftSize:]),dtype = 'uint8')
            byteBufferLength = byteBufferLength - shiftSize
            
            # Check that there are no errors with the buffer length
            if byteBufferLength < 0:
                byteBufferLength = 0         

    return dataOK, frameNumber, detObj

# ------------------------------------------------------------------

# Funtion to update the data and display in the plot
def update():
    dataOk = 0
    # x = []
    # y = []
    # Read and parse the received data
    dataOk, frameNumber, detObj = readAndParseData18xx(Dataport, configParameters)
    
    # if dataOk and len(detObj["x"])>0:
    #     print(detObj["numObj"])
    #     # print(frameNumber)
    #     x = -detObj["x"]
    #     y = detObj["y"]
    
    return dataOk, detObj



data_queue = queue.Queue()

df_columns = ['x', 'y', 'z', 'velocity', 'intensity']
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


def get_radar_data():

# -------------------------    MAIN   -----------------------------------------  

    # Configurate the serial port
    CLIport, Dataport = serialConfig(configFileName)

    # Get the configuration parameters from the configuration file

    
    # Main loop 
    detObj = {}  
    frameData = {}    
    currentIndex = 0
    while True:
        try:
            # Update the data and check if the data is okay
            dataOk, frameNumber, detObj = update()
            # print(dataOk)
            
            if dataOk:
                # Store the current frame into frameData
                data_queue.put(detObj)
            
            time.sleep(0.05) # Sampling frequency of 30 Hz
            
        # Stop the program and close everything if Ctrl + c is pressed
        except KeyboardInterrupt:
            CLIport.write(('sensorStop\n').encode())
            CLIport.close()
            Dataport.close()
            break
        


def update_skeleton(joints, bones, x, y, z):
    joints._offsets3 = (x, y, z)

    for bone, conn in zip(bones, bone_list):
        bone.set_data([x[conn[0]], x[conn[1]]], [y[conn[0]], y[conn[1]]])
        bone.set_3d_properties([z[conn[0]], z[conn[1]]])

def main():

    data_thread = threading.Thread(target=get_radar_data, daemon=True)
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

    skeleton_model = tf.keras.models.load_model("model/MARS.h5")
    to_esp = serial.Serial('/dev/ttyUSB0')

    while True:
        data = data_queue.get()

        point_cloud = pd.DataFrame(data)
        point_cloud["intensity"] = point_cloud["snr"] / 10
        # sort by x, then y for equal x, then z for equal x and y
        point_cloud = point_cloud.sort_values(by=["x", "y", "z"])
        # drop values based on -1 < x < 1
        point_cloud = point_cloud.drop(point_cloud[point_cloud.x < -1].index)
        point_cloud = point_cloud.drop(point_cloud[point_cloud.x > 1].index)
        # drop values based on -1 < z < 1
        point_cloud = point_cloud.drop(point_cloud[point_cloud.z < -1].index)
        point_cloud = point_cloud.drop(point_cloud[point_cloud.z > 1].index)
        # drop values based on 0 < y < 3
        point_cloud = point_cloud.drop(point_cloud[point_cloud.y < 0].index)
        point_cloud = point_cloud.drop(point_cloud[point_cloud.y > 3].index)
        point_cloud = point_cloud.reset_index()
        point_cloud = point_cloud.drop(["index", "snr", "noise"], axis=1)
        # cut data to first 64 points, and zero pad if under
        df_final = point_cloud.reindex(range(64), fill_value=0)
        # convert dataframe to 64x5 column vector
        column_vector = df_final.values
        # convert column vector to square 8x8x5 matrix in row-major order
        square_matrix = np.array([column_vector.reshape(8, 8, 5)])
        skeleton = skeleton_model.predict(square_matrix)
        x = skeleton[0][0:19]
        y = skeleton[0][19:38]
        z = skeleton[0][38:57]
    
        for index in range(19):
            # how do we want to send this?
            x = bytearray(struct.pack("f", skeleton[0][index]))
            y = bytearray(struct.pack("f", skeleton[0][19 + index]))
            z = bytearray(struct.pack("f", skeleton[0][38 + index]))

            packet = x + y + z
            
            to_esp.write(packet)



if __name__ == "__main__":
    main()