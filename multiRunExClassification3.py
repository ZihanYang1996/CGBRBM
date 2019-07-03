#
# -*- coding: utf-8 -*-

# import
import os
import time
from datetime import timedelta
import numpy as np
import tensorflow as tf
from sklearn.cluster import DBSCAN
import data_util
from tfrbm.cgbrbm import CGBRBM
import matplotlib.pyplot as plt
# from sklearn.manifold import TSNE
from MulticoreTSNE import MulticoreTSNE as TSNE
import pickle
import hdbscan
import math


# 总体时间
total_start_time = time.time()


# define functions
def get_time_dif(start_time):
    """获取已使用时间"""
    end_time = time.time()
    time_dif = end_time - start_time
    return timedelta(seconds=int(round(time_dif)))


def print_tsne(data, label, color):
    for _ in data:
        c = color
        m = "^"
        plt.scatter(_[0], _[1], c=c, marker=m, label=label)
    print(label, 'finished')


# %% define variables
base_data_dir = '../Data/Image_Classification'  # 所有数据文件夹的根目录

chanel_increase = 6  # 第一层卷积后的chanel数量 16
filter_height = 3  # 卷积核尺寸 5
filter_width = 3  # 卷积核尺寸 5
offset_height = 55  # 截取图片的起始高度（从上至下）80 ex:55
offset_width = 145  # 截取图片的其实宽度（从左至右）270 ex:145
target_height = 750  # 截取图片的高度 350 ex:750
target_width = 950  # 截取图片的宽度 350 ex:950
resize_height = 64  # 缩放图片的高度 64
resize_width = 64  # 缩放图片的宽度 64
resize_method = 3  # 缩放图片的方式 0

num_each_cat = 250  # 每类文件提取多少
total_spy = 6  # spy 的总数量，目前6个，三类，之后测试更多类的时候再更改
n_epochs = 10
spy_batch_size = 6  # spy的batch数量
batch_size = 30  # 输入文件的batch数量
n_visible = int(resize_height / 4 * resize_width / 4) * (chanel_increase * 2)  # 显层数量（自动计算）
n_hidden = 1000  # 隐层数量 3000
cycle = 10

critical_error = 0
incorrect_sum = []
accuracy = []
cycleCounter = 0
for times in range(cycle):
    # %% loading data & initilize cgbrbm...
    cycleCounter += 1
    print("-------------------nCycle: "+ cycleCounter + "-----------------------")
    print("loading data & initilize cgbrbm...")
    cgbrbm = CGBRBM(n_visible,  # initialize cgbrbm
                    n_hidden,
                    chanel_increase,
                    filter_height,
                    filter_width,
                    offset_height,
                    offset_width,
                    target_height,
                    target_width,
                    resize_height,
                    resize_width,
                    resize_method)
    
    x_train, y_train, total_cat = data_util.create_raw_data(base_data_dir, num_each_cat)  # 得到输入，和一共多少种类total_cat
    x_spy, y_spy = data_util.create_spy_data(base_data_dir, total_spy)  # spy 要用平均质量的图片
    
    # %% Training and evaluating...
    print('Training and evaluating...')
    errs = cgbrbm.cfit(x_train, y_train, n_epochs=n_epochs, batch_size=batch_size)  # train cgbrbm and get error
 
    # %% Getting hidden layers & labels...
    print('Getting hidden layers & labels...')
    start_time = time.time()
    # get inpu hidden layers
    total_input = num_each_cat * total_cat + total_spy  # 得到全部数据，所有非spy输入+所有spy
    hidden_layers = np.zeros((total_input, n_hidden))  # 创建numpy array，大小（所有输入，隐层数量）
    hidden_layer_counter = 0
    for file in os.listdir('./pickle')[0:int(math.ceil(total_cat * num_each_cat / batch_size))]:  # 所有非spy输入
        with open('./pickle/' + file, 'rb') as p:  # 从保存的pickle文件载入数据
            temp = pickle.load(p)
            hidden_layers_batch = cgbrbm.ctransform(temp, batch_size=batch_size)  # 得到hidden layer
            for i in range(len(hidden_layers_batch)):
                hidden_layers[hidden_layer_counter] = hidden_layers_batch[i]
                hidden_layer_counter += 1
    
    # get spy hidden layers
    spy_hidden_layers = cgbrbm.ctransform_spy(x_spy, y_spy, spy_batch_size)  # 把spy图片进行处理并进行卷积，然后得到隐层
    for i in range(len(spy_hidden_layers)):
        hidden_layers[hidden_layer_counter] = spy_hidden_layers[i]
        hidden_layer_counter += 1
    
    # get input labels 得到所有的输入的label,包括spy，顺序与输入数据的feature一一对应
    label_list = []
    start = int(math.ceil(total_cat * num_each_cat / batch_size) + total_spy / spy_batch_size)
    end = int(start + math.ceil(total_cat * num_each_cat / batch_size))
    for file in os.listdir('./pickle')[start:end]:
        with open('./pickle/' + file, 'rb') as p:
            temp = pickle.load(p)
            label_list.extend([temp[i].decode("utf-8") for i in range(len(temp))])  # 注意要decode
#            print(file)
    
    # get spy labels
    start = end
    for file in os.listdir('./pickle')[start:]:
#        print('--'+file)
        with open('./pickle/' + file, 'rb') as p:
            temp = pickle.load(p)
            label_list.extend([temp[i].decode("utf-8") for i in range(len(temp))])  # 注意： 要用spy_batch_size
    time_dif = get_time_dif(start_time)
    print("Time usage:", time_dif)
    
    # %% TSNE
    print('TSNE...')
    embedded_dim = 2
    tsne = TSNE(n_components=embedded_dim, random_state=0, n_jobs=4)
    np.set_printoptions(suppress=True)
    new_dim_points = tsne.fit_transform(hidden_layers)  # TSNE 对隐层进行降维，得到新的坐标点
    
    # %%对与新坐标点进行dbscan聚类，得到dbscan_label,从0开始每个数字代表坐标点的类别，-1代表噪声
    # 参照 https://www.cnblogs.com/pinard/p/6217852.html 的解释
    print('DBSCAN...')
    dbscan_label = DBSCAN(eps=10, min_samples=10).fit_predict(new_dim_points)  # eps 距离的阈值， min_sample，成为核心所需要的样本的阈值 2.5, 3
    if len(np.unique(dbscan_label)) != total_cat:
        if len(np.unique(dbscan_label)) != 7 or -1 not in dbscan_label:
            critical_error += 1
            tf.reset_default_graph()
            plt.figure()
            plt.scatter(new_dim_points[:, 0], new_dim_points[:, 1], c=dbscan_label)  # 画出dbscan分类后得到的所有坐标，一个颜色是一类
            plt.show()
            print('error*********************\n\n\n')
            continue
#    plt.figure()
#    plt.scatter(new_dim_points[:, 0], new_dim_points[:, 1], c=dbscan_label)  # 画出dbscan分类后得到的所有坐标，一个颜色是一类
#    plt.show()
    
    # %% 通过label将tsne处理后得到的新的坐标的进行分类，目前是三类，（用于验证，实际使用可以不用）
    print('get points seperated by label...')
    start_time = time.time()
    label_16 = []
    label_64 = []
    label_Q = []
    
    for i in range(len(label_list)):
        if label_list[i][29:32] == '016':  # 根据文件名第29位进行识别，一下同理
            label_16.append(np.append(np.copy(new_dim_points[i]), [int(i)]))
        elif label_list[i][29:32] == '064':
            label_64.append(np.append(np.copy(new_dim_points[i]), [int(i)]))
        elif label_list[i][29:33] == 'QPSK':
            label_Q.append(np.append(np.copy(new_dim_points[i]), [int(i)]))
    
    label_16.append(np.append(np.copy(new_dim_points[-6]), [total_input - 6]))
    label_16.append(np.append(np.copy(new_dim_points[-5]), [total_input - 5]))
    label_64.append(np.append(np.copy(new_dim_points[-4]), [total_input - 4]))
    label_64.append(np.append(np.copy(new_dim_points[-3]), [total_input - 3]))
    label_Q.append(np.append(np.copy(new_dim_points[-2]), [total_input - 2]))
    label_Q.append(np.append(np.copy(new_dim_points[-1]), [total_input - 1]))
    
    label_16 = np.array(label_16)  # 变成numpy array
    label_64 = np.array(label_64)
    label_Q = np.array(label_Q)
    time_dif = get_time_dif(start_time)
    print("Time usage:", time_dif)
    
    # %%
    print('Plot TSNE by label...')
    start_time = time.time()
    plt.figure()
    print_tsne(data=label_16, label='16', color='dodgerblue')
    print_tsne(data=label_64, label='64', color='red')
    print_tsne(data=label_Q, label='Q', color='gold')
    plt.show()
    time_dif = get_time_dif(start_time)
    print("Time usage:", time_dif)
    
    # %%使用dbscan_label把坐标点分类，目前是三类，如有更多类需要更改，（用于验证，实际使用可以不用）
    print('get points seperated by dbscan...')
    assert dbscan_label[-6] == dbscan_label[-5]
    assert dbscan_label[-4] == dbscan_label[-3]
    assert dbscan_label[-2] == dbscan_label[-1]
    start_time = time.time()
    dbscan_16 = []
    dbscan_64 = []
    dbscan_Q = []
    counter = 0
    for j in range(total_cat):
        #    assert j < total_cat
        temp_set = []
        counter = 0
        for i in range(len(dbscan_label)):
            if dbscan_label[i] == j:
                temp_set.append(np.append(np.copy(new_dim_points[i]), [int(i)]))
                counter += 1
        print(counter)
        #    assert counter == total_input/total_cat
    
        if dbscan_label[-6] == j:
            dbscan_16 = np.array(temp_set.copy())
        if dbscan_label[-4] == j:
            dbscan_64 = np.array(temp_set.copy())
        if dbscan_label[-2] == j:
            dbscan_Q = np.array(temp_set.copy())
    time_dif = get_time_dif(start_time)
    print("Time usage:", time_dif)
    
    # %% compute accuracy，将通过dbscan和label分类得到的类进行对比，得到算法正确率，incorrect 中包含错误识别的序号，可在label_list中寻找
    incorrect = []
    incorrect.extend(np.setdiff1d(dbscan_16[:, 2], label_16[:, 2]))
    incorrect.extend(np.setdiff1d(label_16[:, 2], dbscan_16[:, 2]))
    incorrect.extend(np.setdiff1d(dbscan_64[:, 2], label_64[:, 2]))
    incorrect.extend(np.setdiff1d(label_64[:, 2], dbscan_64[:, 2]))
    incorrect.extend(np.setdiff1d(dbscan_Q[:, 2], label_Q[:, 2]))
    incorrect.extend(np.setdiff1d(label_Q[:, 2], dbscan_Q[:, 2]))
    incorrect = np.unique(np.array(incorrect))
    incorrect_num = len(incorrect)
    
    correct = total_input - total_spy - incorrect_num
    accuracy = correct / (total_input - total_spy)
    print('Incorrect = ', incorrect_num)
    print('Accuracy = ', accuracy)
    tf.reset_default_graph()
    # %%
    # print('Plot TSNE by dbscan...')
    # start_time = time.time()
    # plt.figure()
    # print_tsne(data=dbscan_16, label='16', color='dodgerblue')
    # print_tsne(data=dbscan_64, label='64', color='red')
    # print_tsne(data=dbscan_Q, label='Q', color='gold')
    # plt.show()
    # time_dif = get_time_dif(start_time)
    # print("Time usage:", time_dif)
accuracy = np.array(accuracy)
total_accuracy = np.average(accuracy)
print('Total Accuracy = ', total_accuracy)
# 总体时间
time_dif = get_time_dif(total_start_time)
print("Total time usage:", time_dif)
#%%

#clusterer = hdbscan.HDBSCAN(min_cluster_size=50)
#cluster_labels = clusterer.fit_predict(new_dim_points)
#plt.figure()
#plt.scatter(new_dim_points[:, 0], new_dim_points[:, 1], c=cluster_labels)  # 画出dbscan分类后得到的所有坐标，一个颜色是一类
#plt.show()
