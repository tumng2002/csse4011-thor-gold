import serial
import time
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn import metrics
import pandas as pd
import pickle
import argparse

from ports import *

# Change the configuration file name
# configFileName = 'AWR1843config.cfg'
# configFileName = "tuned-radar.cfg"
configFileName = "profile_3d.cfg"

byteBuffer = np.zeros(2**15,dtype = 'uint8')
byteBufferLength = 0


# ------------------------------------------------------------------

# Function to configure the serial ports and send the data from
# the configuration file to the radar
def serialConfig(configFileName):
    
    # Open the serial ports for the configuration and the data ports
    
    # Raspberry pi
    CLIport = serial.Serial(cli_usb, 115200)
    Dataport = serial.Serial(data_usb, 921600)
    
    # # Windows
    # CLIport = serial.Serial('COM6', 115200)
    # Dataport = serial.Serial('COM3', 921600)

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

        x = np.zeros(numDetectedObj,dtype=np.float32)
        y = np.zeros(numDetectedObj,dtype=np.float32)
        z = np.zeros(numDetectedObj,dtype=np.float32)
        velocity = np.zeros(numDetectedObj,dtype=np.float32)

        # Read the TLV messages
        for tlvIdx in range(numTLVs):
            
            # word array to convert 4 bytes to a 32 bit number
            word = [1, 2**8, 2**16, 2**24]

            # Check the header of the TLV message
            tlv_type = np.matmul(byteBuffer[idX:idX+4],word)
            idX += 4
            tlv_length = np.matmul(byteBuffer[idX:idX+4],word)
            idX += 4
            # print(tlv_type)
            

            # Read the data depending on the TLV message
            if tlv_type == MMWDEMO_UART_MSG_DETECTED_POINTS:

                # Initialize the arrays
                # x = np.zeros(numDetectedObj,dtype=np.float32)
                # y = np.zeros(numDetectedObj,dtype=np.float32)
                # z = np.zeros(numDetectedObj,dtype=np.float32)
                # velocity = np.zeros(numDetectedObj,dtype=np.float32)
                # intensity = np.zeros(numDetectedObj,dtype=np.float32)
                
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
                
                # Store the data in the detObj dictionary
                # detObj = {"numObj": numDetectedObj, "x": x, "y": y, "z": z, "velocity":velocity}
                # dataOK = 1
            
            # NOISE ALWAYS COMES AFTER POINT CLOUT
            elif tlv_type == 7:
                """
                Data Fields
                int16_t 	snr
                    snr - CFAR cell to side noise ratio in dB expressed in 0.1 steps of dB
                
                int16_t 	noise
                    y - CFAR noise level of the side of the detected cell in dB expressed in 0.1 steps of dB
                """
                noise = np.zeros(numDetectedObj,dtype=np.uint16)
                snr = np.zeros(numDetectedObj,dtype=np.uint16)
                for objectNum in range(numDetectedObj):
                    
                    # Read the data for each object
                    snr[objectNum] = byteBuffer[idX:idX + 2].view(dtype=np.uint16)
                    idX += 2
                    noise[objectNum] = byteBuffer[idX:idX + 2].view(dtype=np.uint16)
                    idX += 2
                detObj = {"x": x, "y": y, "z": z, "velocity":velocity, "snr": snr, "noise": noise}
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
    else:
        numDetectedObj = 0     

    return dataOK, frameNumber, detObj, numDetectedObj

# ------------------------------------------------------------------

# Funtion to update the data and display in the plot
def update(Dataport, configParameters):
     
    dataOk = 0
      
    # Read and parse the received data
    dataOk, _, detObj, numDetectedObj = readAndParseData18xx(Dataport, configParameters)
    
    return dataOk, detObj, numDetectedObj


# -------------------------    MAIN   -----------------------------------------  

USE_MODEL = True
PLOT_DATA = True
COLLECT_DATA = False

def main():

    if COLLECT_DATA:
        parser = argparse.ArgumentParser(description='Filename for saving radar data')
        parser.add_argument('-f,--file',
                            dest='file',
                            type=str,
                            required=True,
                            metavar='name of file',
                            help='Name of bin file in raw-data dir')
        args = parser.parse_args()

        # Open a file
        filename = args.file

    # Configurate the serial port
    CLIport, Dataport = serialConfig(configFileName)

    # Get the configuration parameters from the configuration file
    configParameters = parseConfigFile(configFileName)

    if USE_MODEL:
        keypoint_model = tf.keras.models.load_model("model/radar.h5")
    
    # Main loop
    frameData = {}    
    currentIndex = 0
    numDetectedObj = 0
    num_frames = 0

    fig_raw = plt.figure()
    ax_raw = fig_raw.add_subplot(projection='3d')

    fig_model = plt.figure()
    ax_model = fig_model.add_subplot(projection='3d')

    frames = []
    cached_frames = []

    while True:
        try:
            # Update the data and check if the data is okay
            dataOk, detObj, numDetectedObj = update(Dataport, configParameters)
            # print(dataOk)

            if dataOk:
                # Store the current frame into frameData
                frameData[currentIndex] = detObj
                currentIndex += 1
                # x_raw = detObj["x"]
                # y_raw = detObj["y"]
                # z_raw = detObj["z"]

                point_cloud = pd.DataFrame(detObj)
                point_cloud["intensity"] = point_cloud["snr"] / 10
                frames.append(point_cloud)
                
                if len(frames) == 2:

                    final_point = pd.concat(frames)
                    # sort by x, then y for equal x, then z for equal x and y
                    final_point = final_point.sort_values(by=["x", "y", "z"])
                    X_LIM = 1
                    Z_LIM = 1.5
                    Y_MIN = 1
                    Y_LIM = 3
                    # drop values based on -X_LIM < x < X_LIM
                    final_point = final_point.drop(final_point[final_point.x < -X_LIM].index)
                    final_point = final_point.drop(final_point[final_point.x > X_LIM].index)
                    # drop values based on -Z_LIM < z < Z_LIM
                    final_point = final_point.drop(final_point[final_point.z < -Z_LIM].index)
                    final_point = final_point.drop(final_point[final_point.z > Z_LIM].index)
                    # drop values based on 0 < y < 3
                    final_point = final_point.drop(final_point[final_point.y < Y_MIN].index)
                    final_point = final_point.drop(final_point[final_point.y > Y_LIM].index)
                    
                    final_point = final_point.drop(["snr", "noise"], axis=1)
                    final_point = final_point.reset_index()
                    final_point = final_point.drop(["index"], axis=1)
                    
                    # cut data to first 64 points, and zero pad if under
                    df_final = final_point.reindex(range(64), fill_value=0)
                    # convert dataframe to 64x5 column vector
                    column_vector = df_final.values
                    # convert column vector to square 8x8x5 matrix in row-major order
                    square_matrix = np.array([column_vector.reshape(8, 8, 5)])

                    # SAVE TO FILE HERE
                    if USE_MODEL:
                        skeleton = keypoint_model.predict(square_matrix)
                        x = skeleton[0][0:15]
                        # y = skeleton[0][19:38]
                        y = np.zeros(15)
                        z = skeleton[0][15:30]

                    x_raw = df_final["x"]
                    y_raw = df_final["y"]
                    z_raw = df_final["z"]

                    if PLOT_DATA:
                        ax_raw.clear()
                        if USE_MODEL:
                            ax_model.clear()
                            ax_model.scatter(x, y, z)
                            ax_model.set_xlabel('X Label')
                            ax_model.set_ylabel('Y Label')
                            ax_model.set_zlabel('Z Label')
                            ax_model.axes.set_xlim3d(left=-0, right=1) 
                            ax_model.axes.set_ylim3d(bottom=-1, top=1) 
                            ax_model.axes.set_zlim3d(bottom=1, top=0) 
                        ax_raw.scatter(x_raw, y_raw, z_raw)
                        ax_raw.set_xlabel('X Label')
                        ax_raw.set_ylabel('Y Label')
                        ax_raw.set_zlabel('Z Label')
                        ax_raw.axes.set_xlim3d(left=-X_LIM, right=X_LIM) 
                        ax_raw.axes.set_ylim3d(bottom=0, top=3) 
                        ax_raw.axes.set_zlim3d(bottom=Z_LIM, top=-Z_LIM) 
                        plt.pause(0.05)
                    
                    frames.clear()

                    if COLLECT_DATA:
                        cached_frames.append(column_vector.reshape(8, 8, 5))
                        if len(cached_frames) % 10 == 0:
                            print(len(cached_frames))
                        if len(cached_frames) == 500:
                            training_data = np.array(cached_frames)
                            with open(f"radar_data/{filename}.bin", "wb") as f:
                                pickle.dump(training_data, f)
                                break

        except KeyboardInterrupt:
            break

    CLIport.write(('sensorStop\n').encode())
    CLIport.close()
    Dataport.close()


if __name__ == "__main__":
    main()
