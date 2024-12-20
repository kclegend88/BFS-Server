# -*- coding: utf-8 -*-
"""
    封装HIKCamera功能
"""

import socket
import json
import uuid
import datetime
import threading
import traceback
import ast


class clsHIKCameraClient:

    #实例初始化
    def __init__(self, ip, port):
        self.addr = (ip, port)          # 地址与端口,当前测试使用127.0.0.1无法连接HIK，原因未知
        self.conn = None                # sock套接字实例
        self.bDISCONNECT = True         # 断联标志，为True表示断联
        self.int_reconnect_counter = 0  # 连接重试计数器，连上则清零
        self.bRECVThread = False        # 接收线程运行标志，如对方断开会变为False,系统应尝试重新连接   
        self.recv_buf = []              # 接收缓存区，1001的报文会被填入该缓存
        self.int_heart_counter = 0      # 心跳计数器，每次重联时清零，5s一次
        self.int_msg_counter = 0        # 报文计数器，首次建立连接时清零，重联不清零
        self.bShutDown = False          # 如为 True 表示 外部通知 通讯线程应结束
        self.bExit = False              # 如为 True 表示 通讯线程 已结束


    #创建Socket套接字，返回值为True表示连接成功 
    def connect(self):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.conn.connect(self.addr)
            self.bDISCONNECT = False        # 清理断联标志 
            self.int_reconnect_counter = 0  # 清理连接重试计数器
            return True
            
        except Exception as e:
            self.bDISCONNECT = True         # 连接失败，标记断联
            self.int_reconnect_counter = self.int_reconnect_counter + 1     # 累加连接重试计数器
            self.int_heart_counter = 0      # 清理心跳计数器，每次重联时清零，5s一次
            raise Exception(traceback.format_exc())     
            # Todo 后续每三次重连失败之后，放入一个长时间的sleep，避免频繁重连被ban
            return False
 
        else:                               # 预留其他异常的出口
            return False
 
 
    def isConnected(self):                  # 返回连接状态，True表示连接
        return not self.bDISCONNECT
 
 
    #启动 socket 监听线程,每次重连后主程序均会调用此线程
    def start_recv_thread(self):
        if not self.bRECVThread:            # 如果没有线程在运行
            threading.Thread(target=self.recv_thread).start()
            self.bRECVThread = True
            self.int_heart_counter = 0      # 清理心跳计数器，每次重联时清零，5s一次
 
    #socket 监听线程
    def recv_thread(self):
        while True:
            try:
                data = self.conn.recv(1024) # 堵塞至收到数据为止
                if self.bShutDown:          # 如果收到外部的停止命令，则退出线程
                    self.bExit = True;      # 通知外部程序，本线程已终止
                    break;
                if data == 0:               # 返回 0 表示对方已关闭连接
                    self.bDISCONNECT = True
                    self.bRECVThread = False
                    return False            # ToDo 后续可考虑通知主线程关闭的具体时间
                else:
                     self.get_recv(data)    # 收到数据，传递给数据处理子程序
            except Exception as e:
                self.bDISCONNECT = True
                self.bRECVThread = False
                print("连接被关闭-2"+traceback.format_exc())     # ToDo 后续可增加logger或msg，通报主线程
                return False        

    #数据处理函数 区分心跳与数据
    def get_recv(self, data):
        recv_data = data.decode('utf-8')        # b'' Byte类型转成json字符串
        dict_recv_data = ast.literal_eval(recv_data)  # json字符串串行化成字典
        data_type = dict_recv_data["type"]      # 确认消息类型，9000为心跳信号，1001为报文
        if data_type == 9000:                   # 心跳    
            self.int_heart_counter = self.int_heart_counter + 1 
            return 
        elif data_type == '1001':               # 收到正式报文（为什么不是数字1001尚不清楚）
            self.int_msg_counter = self.int_msg_counter + 1
            # print(f"barcode msg= {json_recv_data}")   # ToDo后续加入报文源文存储功能
            self.recv_buf.append(dict_recv_data)        # 压入缓冲区，由主程序处理
        else:
            print(f"data_type= {data_type}")            # 类型异常出口 ToDo 加入异常处理
            
            
    #将缓冲区内的数据，发送至服务器
    def send(self, data):
        if not self.bDISCONNECT:
            self.conn.sendall(data)
        else:
            raise ConnectionError("Connection closed.")


    #生成心跳数据
    def heart(self):
        uuid1 = uuid.uuid1()                        # 生成基于时间的UUID
        uuid_str = str(uuid1).replace('-', '')      # 将UUID转换为字符串
        reqCode = uuid_str[:20]                     # 截取前20位
        heart_data = {
            "type": 9000,
            "reqTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reqCode": reqCode
        }
        heart_data = json.dumps(heart_data).encode("utf-8")
        return heart_data


