import serial
import time
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from sklearn import metrics
import pandas as pd

# Change the configuration file name
# configFileName = 'AWR1843config.cfg'
# configFileName = "tuned-radar.cfg"
configFileName = "profile_3d.cfg"

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
    
    # Windows
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
            print(tlv_type)
            

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

    return dataOK, frameNumber, detObj, numDetectedObj

# ------------------------------------------------------------------

# Funtion to update the data and display in the plot
def update():
     
    dataOk = 0
      
    # Read and parse the received data
    dataOk, _, detObj, numDetectedObj = readAndParseData18xx(Dataport, configParameters)
    
    return dataOk, detObj, numDetectedObj


# -------------------------    MAIN   -----------------------------------------  

# Configurate the serial port
CLIport, Dataport = serialConfig(configFileName)

# Get the configuration parameters from the configuration file
configParameters = parseConfigFile(configFileName)

keypoint_model = tf.keras.models.load_model("../ml_model/model/MARS.h5")
   
# Main loop
frameData = {}    
currentIndex = 0

fig = plt.figure()

ax = fig.add_subplot(projection='3d')
plot = True

while True:
    try:
        # Update the data and check if the data is okay
        dataOk, detObj, numDetectedObj = update()
        # print(dataOk)

        if dataOk:
            # Store the current frame into frameData
            frameData[currentIndex] = detObj
            currentIndex += 1
            x_raw = detObj["x"]
            y_raw = detObj["y"]
            z_raw = detObj["z"]
            point_cloud = pd.DataFrame(detObj)
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
            skeleton = keypoint_model.predict(square_matrix)
            x = skeleton[0][0:19]
            y = skeleton[0][19:38]
            z = skeleton[0][38:57]

            if plot:
                ax.clear()
                ax.scatter(x, y, z)
                ax.scatter(x_raw, y_raw, z_raw)
                ax.set_xlabel('X Label')
                ax.set_ylabel('Y Label')
                ax.set_zlabel('Z Label')
                ax.axes.set_xlim3d(left=-1, right=1) 
                ax.axes.set_ylim3d(bottom=0, top=3) 
                ax.axes.set_zlim3d(bottom=-1, top=1) 
                plt.pause(0.05)
        # Update the data and check if the data is okay
        # dataOk = update()
        # # print(dataOk)
        
        # if dataOk:
        #     # Store the current frame into frameData
        #     frameData[currentIndex] = detObj
        #     currentIndex += 1
        
        # time.sleep(0.05) # Sampling frequency of 30 Hz
        
    # Stop the program and close everything if Ctrl + c is pressed
    except KeyboardInterrupt:
        CLIport.write(('sensorStop\n').encode())
        CLIport.close()
        Dataport.close()
        break
        
    





