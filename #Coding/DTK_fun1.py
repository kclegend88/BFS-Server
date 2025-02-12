import datetime
import logging

import random
import string

import pandas as pd

import mysql
from DTK import *


class SendData:  # 报文定义类
    PackageId = 0

    def __init__(self):
        current_time = datetime.datetime.now()  # 获取当前的日期和时间
        self.CreateTime = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")  # 格式化日期和时间
        self.now_time = current_time.strftime("%Y%m%d%H%M%S")  # 格式化日期和时间
        random_letters = ''.join(random.choice(string.ascii_letters) for _ in range(4))
        self.reqCode = '%02d' % random.randint(0, 99) + random_letters + '%04d' % random.randint(0,
                                                                                                 9999) + self.now_time

    def pgid_add(self):
        SendData.PackageId += 1
        return SendData.PackageId

    # WCS 向通道机发起读取请求的数据
    def sendBarcode(self, barcode, Qty):
        Type = 1001

        # 请求编号:
        # 两位随机数+4位随机字母+4位随机数+时间
        PackageId = self.pgid_add()  # 此数据要求唯一
        Barcode = barcode
        Op = 1
        data = {
            "CreateTime": self.CreateTime,
            "Type": Type,
            "ReqCode": self.reqCode,
            "PackageId": PackageId,
            "Barcode": Barcode,
            "Op": Op,
            "Qty": Qty,
            "result": 0
        }
        byte_string = json.dumps(data).encode()  # josn转为字节类型
        hex_byte = len(byte_string).to_bytes(4, byteorder='big')
        final_data = b'\x02' + hex_byte + byte_string + b'\x03'
        return final_data

    def read_feedback(self, packageID, barcode):  # 读取反馈
        # 请求编号:
        # 两位随机数+4位随机字母+4位随机数+时间
        PackageId = packageID  # 此数据要求唯一
        Type = 2002
        Barcode = barcode
        Op = 0
        data = {
            "CreateTime": self.CreateTime,
            "Type": Type,
            "ReqCode": self.reqCode,
            "PackageId": PackageId,
            "Barcode": Barcode,
            "Op": Op,
            "Qty": 0,
            "result": 1
        }
        byte_string = json.dumps(data).encode()  # josn转为字节类型
        hex_byte = len(byte_string).to_bytes(4, byteorder='big')
        final_data = b'\x02' + hex_byte + byte_string + b'\x03'
        return final_data

    def heart(self):
        PackageId = 0
        Barcode = 'null'
        Type = 9001
        data = {
            "CreateTime": self.CreateTime,
            "Type": Type,
            "ReqCode": self.reqCode,
            "PackageId": PackageId,
            "Barcode": Barcode,
            "Op": 0,
            "Qty": 0,
            "result": 0
        }
        byte_string = json.dumps(data).encode()  # josn转为字节类型
        hex_byte = len(byte_string).to_bytes(4, byteorder='big')
        final_data = b'\x02' + hex_byte + byte_string + b'\x03'
        return final_data


def status():  # 查 运行状态
    sbutton = {'start': StartButton.start, 'busy': StartButton.busy, 'error': StartButton.error,
               'data_bindEPC': StartButton.data_bindEPC}
    print(sbutton)
    return sbutton


class StartButton:  # 按钮交互类
    # 类变量定义
    start = 0  # 开始
    busy = 0  # 忙碌
    error = 0  # 异常, 1表示未找到对应的大条码
    data_bindEPC = []
    bind_osn = []
    fx_id = ''

    def __init__(self):
        pass

    def csv_proofread(self, container_number, client_object):
        try:
            container_without = container_number  # 界面输入的大箱号
            Qty = 50
            StartButton.fx_id = container_number
            sd = SendData().sendBarcode(container_without, Qty)  # 进入指令
            client_object.conn.send(sd)  # 发送
            # 云端获取数据库 对应psn绑定的osn
            psn = mysql.select_psn(container_without)
            StartButton.data_bindEPC = mysql.get_orderinfo_osn(psn)[1]
            logging.info(f"获取到绑定的EPC:{StartButton.data_bindEPC}")
            StartButton.bind_osn = mysql.get_orderinfo_osn(psn)[0]
            StartButton.busy = 1  # 改为忙碌状态
            return {'result': 1}
        except Exception as e:
            print(e)


class Status:  # 程序运行状态
    recv_barcode = 0
    result = 0
    barcodes_dict = {}

    def __init__(self):
        pass

    def reset_status(self, start, busy, error):
        StartButton.start = start
        StartButton.busy = busy
        StartButton.error = error

    def check_status(self):
        start = StartButton.start
        busy = StartButton.busy
        error = StartButton.error
        # print(f"start: {start}, busy: {busy}, error: {error}")
        return {'start': start, 'busy': busy, 'error': error}

    def back_1(self):
        StartButton.start = 1

def back_2(recv_data):
    print(f"通道机返回的数据{recv_data}")



def createexcel(data):
    scan_barcodes = data  # 列表
    # 将列表转换为 DataFrame
    df = pd.DataFrame(scan_barcodes, columns=["Barcode"])

    # 保存为 Excel 文件
    df.to_excel('scan_barcodes.xlsx', index=False)

    print("Excel 文件保存成功！")