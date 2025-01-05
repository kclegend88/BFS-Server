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
import time
import re

class clsHIKCameraClient:

    #实例初始化
    def __init__(self, ip, port):
        self.addr = (ip, port)          # 地址与端口,当前测试使用127.0.0.1无法连接HIK，原因未知
        self.conn = None                # sock套接字实例
        self.bDISCONNECT = True         # 断联标志，为True表示断联
        self.bRECVThread = False        # 监听线程运行标志位，如对方断开会变为False,系统应尝试重新连接   
        self.bRecvValidData = False     # 收到有效数据
        self.bExit = False              # 线程退出标志位
        self.int_reconnect_counter = 0  # 连接重试计数器，连上则清零
        self.int_heart_counter = 0      # 心跳计数器，每次重联时清零，5s一次
        self.int_msg_counter = 0        # 报文计数器，首次建立连接时清零，重联不清零
        self.int_thread_counter = 0     # 线程计数器，每次新开一个线程加一
        self.recv_buf = []              # 接收缓存区，b''格式，1001的报文原文会被填入该缓存
        self.lstException = []          # 异常消息清单，字典格式,用于存储通讯过程中所发生的全部异常消息
        self.lstValidData = []          # 有效数据缓存区，字典格式
        self.threadhandler = None       # 
        self.intValidFaultNo= 0         
        self.lstUnpackBuf = []

    def append_exception(self, subfunc, msg):
        self.lstException.append(
            {'module': f'clsHIKCameraClient.{subfunc}',
             'timestamp': datetime.datetime.now().isoformat(),
             'msg': msg})

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
            self.int_heart_counter = 0      # 清理心跳计数器，每次重联时清零
            self.append_exception("connect", "连接失败:%s"%(traceback.format_exc(),))
            # Todo 后续每三次重连失败之后，放入一个长时间的sleep，避免频繁重连被ban
            return False
 

    #启动 socket 监听线程,每次重连后主程序均会调用此线程
    def start_recv_thread(self):
        if not self.bRECVThread:            # 如果没有线程在运行
            self.threadhandler = threading.Thread(target=self.recv_thread).start()
            self.int_thread_counter = self.int_thread_counter + 1
            self.bExit = False 
 
    #socket 监听线程
    def recv_thread(self):
        while True:
            try:
                self.bRECVThread = True
                data = self.conn.recv(1024) # 堵塞至收到数据为止
                if not data:                    # 返回 空 表示对方已关闭连接
                    self.bDISCONNECT = True     # 设置断连标志
                    self.bRECVThread = False    # 标记监听线程已终止
                    self.append_exception("recv_thread", "连接已被对方关闭:%s"%(traceback.format_exc(),))
                    break                      # ToDo 后续可考虑通知主线程关闭的具体时间
                # 收到不为空的数据
                # ToDo  如果收到超长数据，需要存下来
                #       上次缓存的校验失败数据，与本次读取的拼成一个包，再校验一次
                self.lstUnpackBuf = self.unpack_buf(data)
                for i,data_item in enumerate(self.lstUnpackBuf):
                    validdata = self.check_recvbuf(data_item)    # 数据校验
                    if validdata:    # 数据有效性校验通过
                        data_type = validdata['type']           # 确认消息类型，9000为心跳信号，1001为有效报文
                        if data_type == 9000:                   # 心跳信号    (数字 9000)
                            self.int_heart_counter = self.int_heart_counter + 1 
                        elif data_type == '1001':               # 收到正式报文（字符串1001尚不清楚）
                            self.int_msg_counter = self.int_msg_counter + 1
                            self.convert_recvbuf(validdata)     # 数据处理函数，将缓冲区内的数据转换成期望的dict格式 
                            self.recv_buf.append(data)          # only for debug/接收缓冲区的原文
                            if len(self.lstValidData ) > 10:        # 有效数据缓冲区太满，说明主线程处理太慢
                                self.append_exception("recv_thread", "有效数据缓冲区内数据过多，请及时处理！！")
                    else:                                   # 未预料的数据包，或超长数据
                        self.append_exception("recv_thread", "接收缓冲区校验失败,错误代码%d, 缓存区数据:%s"
                                  %(self.intValidFaultNo,data.decode('utf-8')))
                        # ToDo缓存校验失败的数据，与下一次读取的拼成一个包，再校验一次
                self.lstUnpackBuf.clear()
                time.sleep(0.1)        
            except Exception as e:
                self.bDISCONNECT = True
                self.bRECVThread = False
                self.append_exception("recv_thread", "监听线程异常退出,线程编号%d, 异常信息:%s"
                          %(self.int_thread_counter,traceback.format_exc()))
                break       
        self.append_exception("recv_thread", "线程退出，编号:%d"%(self.int_thread_counter,))
        time.sleep(3)       # 等待exception 消息输出
        self.bExit = True
    
    # 缓存区数据的拼接和分割
    def unpack_buf(self,data_buf):
        lst_uppack_buf = []
        recv_data = data_buf.decode('utf-8')            # b'' Byte类型转成json字符串
        # 如果数据长度小于1024，只有一个{ 只有一个} 直接返回
        if recv_data.startswith('{'):                 # 完整前缀
            if recv_data.endswith('}'):               # 完整后缀
                if recv_data.find('}{') == -1:       # 不存在包黏连
                    lst_uppack_buf.append(recv_data)
                    
                else:                               # 有包黏连
                    new_recv_data = recv_data.replace('}{','}^{')
                    lst_uppack_buf = new_recv_data.split('^')
                    self.append_exception("unpack_buf", "发现黏连的数据包，个数:%d"%(len(lst_uppack_buf),))
                return lst_uppack_buf
            else:                                   # 后缀不完整，ToDo要将这段数据存起来，等着下一次读取的拼在一起
                self.append_exception("unpack_buf", "发现数据包后缀不完整")
                return None
        else:                                       # 开头不完整，ToDo要与上一次的数据拼在一起
            self.append_exception("unpack_buf", "发现数据包前缀不完整")
            return None 
        

    
    # 数据处理函数 判断数据长度，区分数据类型，尝试拼接数据，如拼接异常则需要输出停机指令
    def check_recvbuf(self, data_buf):
        # 首先检查数据完整性，如果数据完整且小于缓冲区总长度，则直接输出
        # 如果不完整，先判断数据长度，如果长度达到接收缓冲区的最大长度(1024），则有可能报文需要拼接,存入内部缓存等待拼接
        # 每次收数据都查历史拼接异常的，如果拼接异常的数据收到之后，已有至少两个完整数据输出，则认为拼接无望，需要输出报错信息
        # 一个超长报文可能是多条码（例如超过50个条码)，一旦收到这样的信息，要谨慎对待，有可能需要立刻停机
        try:
            recv_data = data_buf            # json字符串
            # recv_data = data_buf.decode('utf-8')            # b'' Byte类型转成json字符串
            #Todo 判断 是否包含非法字符
            # str_re = u'!@#$%^&*()-=_+'
            # if "?" in data:
                # logger.error("数据包含非法字符")
            #    print(f"数据包含非法字符:{data}")
            # return None
            dict_recv_data = ast.literal_eval(recv_data)    # json字符串串行化成字典
            #Todo 查找uid、reqTime、reqCode、read、code、type是否在keys中
            
        except Exception as e:
            self.append_exception("check_recvbuf", "数据解析出现异常: %s"%(traceback.format_exc(),))
            return None        
        PassedDict = {}
        # print(dict_recv_data) 
        reqTime = dict_recv_data['reqTime']
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", reqTime):
            PassedDict['reqTime'] = reqTime
        else:
            self.intValidFaultNo =101
            return None
        datatype = dict_recv_data['type']
        if datatype in ['1001', 9000]:
            PassedDict['type'] = datatype
        else:
            self.intValidFaultNo =102
            return None

        if datatype == 9000:
            reqCode = dict_recv_data['reqCode']
            if len(reqCode) == 20:
                PassedDict['reqCode'] = reqCode
                return PassedDict
            else:
                self.intValidFaultNo =103
                return None
        
        reqCode = dict_recv_data['regCode']
        if len(reqCode) == 36 and len(reqCode.replace("-", "")) == 32:
            PassedDict['reqCode'] = reqCode
        else:
            self.intValidFaultNo =104
            return None
        uid = dict_recv_data['uid']
        ReadType = dict_recv_data['read']
        if len(uid) == 36 and len(uid.replace("-", "")) == 32:
            PassedDict['uid'] = uid
        else:
            self.intValidFaultNo =105
            return None
        if ReadType in ['AlRead', 'NoRead', 'ErrRead']:
            PassedDict['read'] = ReadType
        else:
            self.intValidFaultNo =106
            return None
        code = dict_recv_data['code']
        if isinstance(code, list):
            PassedDict['code'] = code
        else:
            self.intValidFaultNo =107
            return None
        coordinate = dict_recv_data['coordinate']
        CenterCoordinate = self.locate_coordinates(coordinate)
        if CenterCoordinate:
            PassedDict['coordinate'] = CenterCoordinate
        else:
            self.intValidFaultNo =108
            return None
        return PassedDict

    def locate_coordinates(self,coordinate: dict):
        try:
            XSum = 0
            YSum = 0
            for key,value in coordinate.items():
                if -200 < value and value < 3000:
                    pass
                else:
                    return False
                if 'X' in key:
                    XSum = XSum + value
                elif 'Y' in key:
                    YSum = YSum + value

            center_x = XSum // 4
            center_y = YSum // 4
            return {'x': center_x, 'y': center_y}
        except Exception as e:
            self.append_exception("check_recvbuf", "数据解析出现异常: %s"%(traceback.format_exc(),))

        
    # 数据处理函数,将处理完成的数据插入lstValidData,并标记bRecvValidData = True
    def convert_recvbuf(self, dict_recv_data):
     
        dictValidData = {}
        dictValidData['uid'] = dict_recv_data['uid']
        dictValidData['req_ts'] = dict_recv_data['reqTime']

        code = dict_recv_data['code']
        ReadResult = dict_recv_data['read']
        ReadType = dict_recv_data['type']

        position = dict_recv_data['coordinate']
        dictValidData['pos_x'] = position['x']
        dictValidData['pos_y'] = position['y']

        self.int_msg_counter = self.int_msg_counter + 1
        if ReadResult == 'AlRead' and len(code) == 1:
            dictValidData['code'] = code[0]
            dictValidData['result'] = 'GR'
            self.lstValidData.append(dictValidData.copy())
            self.bRecvValidData = True
        elif ReadResult == 'NoRead' and not code:
            dictValidData['code'] =''
            result = 'NR'
            dictValidData['result'] = 'NR'
            self.lstValidData.append(dictValidData.copy())
            self.bRecvValidData = True
        elif ReadResult == 'ErrRead' and len(code) > 1:
            dictValidData['result'] = 'MR'
            tempuid = dictValidData['uid']
            for i,d in enumerate(code):   
                dictValidData['uid'] = f"{tempuid}-%d"%(i,)
                dictValidData['code'] = d
                self.lstValidData.append(dictValidData.copy())
            self.bRecvValidData = True
        else:
            self.append_exception("check_recvbuf", "数据解析出现异常")

        
    #将缓冲区内的数据，发送至服务器
    def send(self, data):
        if not self.bDISCONNECT:
            self.conn.sendall(data)
            return True
        else:
            self.append_exception("check_recvbuf", "连接尚未建立,无法发送数据")
            return False

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

    # 关闭套接字
    def shutdown(self):
        self.conn.close()
        return

