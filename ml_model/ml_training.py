import matplotlib.pyplot as plt
import numpy as np 
import tensorflow as tf
from sklearn import metrics
from sklearn.model_selection import train_test_split
import pandas as pd
import pickle

from keras.optimizers import Adam
from keras.models import Model
from keras.layers import Dense
from keras.layers import Input
from keras.layers import Flatten
from keras.layers import Conv2D
from keras.layers.normalization.batch_normalization import BatchNormalization
from keras.layers import Dropout


"""
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
"""


def load_labeled_data():
    joint_num = np.array([0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30])
    training_data_file_names = ["arms-up.bin", "t-pose.bin", "arms-down.bin"]
    pose_frames = []
    for filename in training_data_file_names:
        # df = pd.DataFrame
        with open(f"training_data/{filename}", "rb") as f:
            dataset = pickle.load(f)
            
        frames = []
        
        for i in range(2000):
            x = []
            z = []
            for j, landmark in enumerate(dataset[i].landmark):
                if j not in joint_num:
                    continue
                x.append(landmark.x)
                z.append(landmark.y)
            x = np.array(x)
            z = np.array(z)
            frame = np.append(x, z)
            frames.append(frame)
        filtered_data = np.array(frames)
        pose_frames.append(filtered_data)
    output_data = np.concatenate([pose_frames[0], pose_frames[1], pose_frames[2]], axis=0)
    print(output_data.shape)
    return output_data


def load_training_data():
    training_data_file_names = ["arms-up.bin", "t-pose.bin", "arms-down.bin"]
    pose_frames = []
    for filename in training_data_file_names:
        # df = pd.DataFrame
        with open(f"radar_data/{filename}", "rb") as f:
            dataset = pickle.load(f)
        pose_frames.append(dataset)
    output_data = np.concatenate([pose_frames[0], pose_frames[1], pose_frames[2]], axis=0)
    print(output_data.shape)
    return output_data


def define_CNN(in_shape, n_keypoints):

    in_one = Input(shape=in_shape)
    conv_one_1 = Conv2D(16, kernel_size=(3, 3), activation='relu', strides=(1, 1), padding = 'same')(in_one)
    conv_one_1 = Dropout(0.3)(conv_one_1)
    conv_one_2 = Conv2D(32, kernel_size=(3, 3), activation='relu', strides=(1, 1), padding = 'same')(conv_one_1)
    conv_one_2 = Dropout(0.3)(conv_one_2)

    conv_one_2 = BatchNormalization(momentum=0.95)(conv_one_2)

    fe = Flatten()(conv_one_2)
    # dense1
    dense_layer1 = Dense(512, activation='relu')(fe)
    dense_layer1 = BatchNormalization(momentum=0.95)(dense_layer1)
    # # dropout

    # dropout
    dense_layer1 = Dropout(0.4)(dense_layer1)
    
    out_layer = Dense(n_keypoints, activation = 'linear')(dense_layer1)
    

    # model
    model = Model(in_one, out_layer)
    opt = Adam(lr=0.001, beta_1=0.5)

    # compile the model
    model.compile(loss='mse', optimizer=opt, metrics=['mae', 'mse', 'mape', tf.keras.metrics.RootMeanSquaredError()])
    return model


# define batch size and epochs
batch_size = 128
epochs = 150


def main():
    # #load the feature and labels, 24066, 8033, and 7984 frames for train, validate, and test
    # featuremap_train = np.load('feature/featuremap_train.npy')
    # featuremap_validate = np.load('feature/featuremap_validate.npy')
    # featuremap_test = np.load('feature/featuremap_test.npy')

    # labels_train = np.load('feature/labels_train.npy')
    # labels_validate = np.load('feature/labels_validate.npy')
    # labels_test = np.load('feature/labels_test.npy')
    # remove the arms up one
    training_data_file_names = ["arms-up.bin", "t-pose.bin", "arms-down.bin"]
    labeled_data = load_labeled_data()
    training_data = load_training_data()
    X_train, X_test, y_train, y_test = train_test_split(training_data, labeled_data, test_size=0.2)

    keypoint_model = define_CNN(X_train[0].shape, 30)
    # initial maximum error 
    score_min = 10
    history = keypoint_model.fit(X_train, y_train,
                                 batch_size=batch_size, epochs=epochs, verbose=1, 
                                 validation_data=(X_test, y_test))
    # save and print the metrics
    score_train = keypoint_model.evaluate(X_train, y_train, verbose = 1)
    print('train MAPE = ', score_train[3])
    score_test = keypoint_model.evaluate(X_test, y_test, verbose = 1)
    print('test MAPE = ', score_test[3])

        # Plot accuracy
    plt.plot(history.history['mae'])
    plt.plot(history.history['val_mae'])
    plt.title('Model accuracy')
    plt.ylabel('Accuracy')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Xval'], loc='upper left')
    plt.show()
    
    # Plot loss
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss'])
    plt.title('Model loss')
    plt.ylabel('Loss')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Xval'], loc='upper left')
    plt.xlim([0,100])
    plt.ylim([0,0.1])
    plt.show()

    keypoint_model.save("model/radar.h5")

    exit()
    # training_data_file_names = ["squat.bin"]
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    for name in training_data_file_names:
        with open(f"training_data/{name}", "rb") as f:
            training_features = pickle.load(f)
            for i in range(500):
                ax.clear()
                # ax.scatter(landmark.x, landmark.y, landmark.z)
                x = []
                y = []
                z = []
                for landmark in training_features[i].landmark:
                    x.append(landmark.x)
                    y.append(0)
                    z.append(landmark.y)
                    # ax.scatter(landmark.x, landmark.y, landmark.z)
                ax.scatter(x, y, z)
                ax.set_xlabel("X")
                ax.set_ylabel("Y")
                ax.set_zlabel("Z")
                ax.axes.set_xlim3d(left=-0.5, right=0.5)
                ax.axes.set_ylim3d(bottom=-0.5, top=0.5)
                ax.axes.set_zlim3d(bottom=1, top=0)

                plt.pause(0.05)
    
    # plt.show()
    #         # print(training_features[0].landmark[0])


    # # Initialize the result array
    # paper_result_list = []


    # # define batch size and epochs
    # batch_size = 128
    # epochs = 150

    # # load model
    # keypoint_model = tf.keras.models.load_model("model/MARS.h5")
    # # Repeat i iteration to get the average result
    # # for i in range(10):
    # # instantiate the model
    # keypoint_model = tf.keras.models.load_model("model/MARS.h5")

    # # save and print the metrics
    # # score_train = keypoint_model.evaluate(featuremap_train, labels_train,verbose = 1)
    # # print('train MAPE = ', score_train[3])
    # # score_test = keypoint_model.evaluate(featuremap_test, labels_test,verbose = 1)
    # # print('test MAPE = ', score_test[3])
    # print(len(featuremap_test))
    # result_test = keypoint_model.predict(np.array([featuremap_test[2735]]))

    # x = result_test[0][0:19]
    # y = result_test[0][19:38]
    # z = result_test[0][38:57]
    # # print(pts)
    
    # fig = plt.figure()
    # ax = fig.add_subplot(projection='3d')
    # ax.scatter(x, y, z)
    # ax.set_xlabel('X Label')
    # ax.set_ylabel('Y Label')
    # ax.set_zlabel('Z Label')
    # plt.show()

    # # df = pd.DataFrame(result_test)
    # # print(df)
    # # print(featuremap_test)
    # # print(featuremap_test[0])
    # # print(result_test)
    # # print(result_test[0])
    # exit()

    # # instantiate the model
    # # keypoint_model = define_CNN(featuremap_train[0].shape, 57)

    # # # # initial maximum error 
    # # # score_min = 10
    # # history = keypoint_model.fit(featuremap_train, labels_train,
    # #                             batch_size=batch_size, epochs=epochs, verbose=1, 
    # #                             validation_data=(featuremap_validate, labels_validate))
    # # result_test = keypoint_model.predict(featuremap_test)

if __name__ == "__main__":
    main()
