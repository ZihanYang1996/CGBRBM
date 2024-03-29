# coding: utf-8

import sys
from collections import Counter
import numpy as np
import tensorflow as tf
import os
import natsort

# def open_file(filename, mode='r'):
#     return open(filename, mode, encoding='utf-8', errors='ignore')
#
#
# def read_file(filename):
#     contents, labels = [], []
#     with open_file(filename) as f:
#         for line in f:
#             try:
#                 label, content = line.strip().split('\t')
#                 if content:
#                     contents.append(list(content.split('/')))
#                     labels.append(label)
#             except:
#                 pass
#     return contents, labels  # contents: 两维list，包含所有句子，每个句子一个list；labels：list，类

def create_raw_data(dirname, num_each_cat):  # 通过路径和文件名 创建x,y
    cats = []
    data = []
    dirs = os.listdir(dirname)
    for i in dirs:
        temp = os.path.join(dirname, i)
        if os.path.isdir(temp) and i != 'test' and i != 'spy' and i != 'archive' and i != 'result':
            cats.append(temp)
    iterator = iter(cats)
    for i in range(len(cats)):
        dir_temp = next(iterator)
        for root, dirs, files in os.walk(dir_temp):
            print(root)            
            for file in natsort.natsorted(files, reverse=True)[0:num_each_cat]:
                if os.path.splitext(file)[1] == '.jpg':
                    data.append(os.path.join(dir_temp, file))
        print("finished: ", dir_temp)
    return np.array(data), np.array(data), len(cats)


def create_spy_data(dirname, total_spy):
    cats = []
    data = []
    dirs = os.listdir(dirname)
    for i in dirs:
        if i == 'spy':
            cats.append(os.path.join(dirname, i))
    iterator = iter(cats)
    for i in range(len(cats)):
        dir_temp = next(iterator)
        for root, dirs, files in os.walk(dir_temp):
            print(root)
            for file in files[0:total_spy]:
                if os.path.splitext(file)[1] == '.jpg':
                    data.append(os.path.join(dir_temp, file))
        print("finished: ", dir_temp)
    return np.array(data), np.array(data)

def remove_data(dirname, num_each_cat):
    cats = []
    dirs = os.listdir(dirname)
    for i in dirs:
        temp = os.path.join(dirname, i)
        if os.path.isdir(temp) and i != 'test' and i != 'spy' and i != 'archive' and i != 'result':
            cats.append(temp)
    iterator = iter(cats)
    for i in range(len(cats)):
        dir_temp = next(iterator)
        for root, dirs, files in os.walk(dir_temp):
            print(root)
            for file in natsort.natsorted(files, reverse=True)[0:num_each_cat]:                
                if os.path.splitext(file)[1] == '.jpg':
                    os.remove(os.path.join(dir_temp, file))
    print("{} removed".format(num_each_cat))

# def create_raw_data(dirname, num_each_cat):
#     labels = []
#     data = []
#     quam16_dir = os.path.join(dirname, '16QAM')
#     quam64_dir = os.path.join(dirname, '64QAM')
#     qpsk_dir = os.path.join(dirname, 'QPSK')
#     cats = iter([quam16_dir, quam64_dir, qpsk_dir])
#     for i in range(3):
#         dir_temp = next(cats)
#         for root, dirs, files in os.walk(dir_temp):
#             print(root)
#             for file in files[0:num_each_cat]:
#                 if os.path.splitext(file)[1] == '.jpg':
#                     labels.append(os.path.join(dir_temp, file))
#                     data.append(os.path.join(dir_temp, file))
#         print("finished: ", dir_temp)
#     return np.array(data), np.array(labels)
