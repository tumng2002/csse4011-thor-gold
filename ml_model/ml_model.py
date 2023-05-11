import matplotlib.pyplot as plt
import numpy as np 
import tensorflow as tf
from sklearn import metrics

from keras.optimizers import Adam
from keras.models import Model
from keras.layers import Dense
from keras.layers import Input
from keras.layers import Flatten
from keras.layers import Conv2D
from keras.layers.normalization import BatchNormalization
from keras.layers import Dropout




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


def main():
    #load the feature and labels, 24066, 8033, and 7984 frames for train, validate, and test
    featuremap_train = np.load('feature/featuremap_train.npy')
    featuremap_validate = np.load('feature/featuremap_validate.npy')
    featuremap_test = np.load('feature/featuremap_test.npy')

    labels_train = np.load('feature/labels_train.npy')
    labels_validate = np.load('feature/labels_validate.npy')
    labels_test = np.load('feature/labels_test.npy')

    # Initialize the result array
    paper_result_list = []


    # define batch size and epochs
    batch_size = 128
    epochs = 150

    # load model
    keypoint_model = tf.keras.models.load_model("model/MARS.h5")

    # instantiate the model
    keypoint_model = define_CNN(featuremap_train[0].shape, 57)

    # # initial maximum error 
    # score_min = 10
    history = keypoint_model.fit(featuremap_train, labels_train,
                                batch_size=batch_size, epochs=epochs, verbose=1, 
                                validation_data=(featuremap_validate, labels_validate))
    result_test = keypoint_model.predict(featuremap_test)

if __name__ == "__main__":
    main()