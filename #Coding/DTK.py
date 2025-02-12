import json
import queue
import socket
import time
import threading
import traceback

import DTK_fun1

import configparser

DISCONNECT = True


class Client:
    # 创建ConfigParser对象
    config = configparser.ConfigParser()
    break_sign = False
    close_sign = False
    # 读取配置文件
    config.read('config.ini')
    server_ip = config['server']['tdj_ip']
    server_port = int(config['server']['port'])

    def __init__(self, msg_queue):
        self.addr = (Client.server_ip, Client.server_port)
        self.conn = None
        self.msg_queue = msg_queue

    def connect(self):
        global DISCONNECT
        while True:
            print('请求连接服务器...')
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Client.conn = self.conn
            try:
                self.conn.connect(self.addr)
            except Exception as e:
                print(f'服务器{self.addr}连接超时{e}')
                # logger.error(f'服务器{self.addr}连接超时{e}')
                time.sleep(2)
                continue
            else:
                print(f"连接服务器{self.addr}成功")
                DISCONNECT = False
                break

    def run(self):
        global DISCONNECT
        First = True
        while True and not Client.break_sign:
            try:
                if DISCONNECT:
                    print('正在尝试连接...')
                    Client.break_sign = True
                    print('修改成功')
                    self.connect()
                    Client.break_sign = False
                    First = True
                if First:
                    server = Requset(self.conn)
                    re_data = RecvData(self.conn)
                    h = threading.Thread(target=server.hear, args=(self.msg_queue,))
                    r = threading.Thread(target=re_data.handle_recv, args=(self.msg_queue,))
                    First = False
                    b = threading.Thread(target=server.send_heart)
                    h.start()
                    r.start()
                    b.start()
                time.sleep(1)
            except Exception as e:
                # logger.error(e)
                DISCONNECT = True
                time.sleep(2)
        print('run线程关闭')


class Requset:

    # Barcode = config['sendData']['Barcode']
    # PackageID = int(config['sendData']['PackageID'])
    def __init__(self, conn):
        self.conn = conn
    def hear(self, queue):
        global DISCONNECT, data3_main
        # print('进入监听线程')
        while True and not Client.break_sign:
            try:
                data1 = self.conn.recv(1)  # 接收数据
                # logger.info(f'data1: {data1}')
                #  判断数据
                if data1 == b'\x02':
                    data2 = self.conn.recv(4)
                    data2_int = int.from_bytes(data2, byteorder='big')  # 字节类型转化为进制整数
                    data3 = self.receive_exact_length(data2_int)

                    data3_main = data3.decode('utf-8')  # 取出json数据
                    data3_main = json.loads(data3_main)

                    data4 = self.conn.recv(1)
                    if data4 == b'\x03':
                        #print(f'接收到报文为: {data3_main}')
                        # logger.info(f'接收到完整字节数据为: {data1 + data2 + data3 + data4}')
                        queue.put(data3_main)
                    else:
                        while True:
                            data = self.conn.recv(1024)
                            if not data:
                                break
                        # raise ValueError('没有读到结束字节0x03')

                else:
                    continue
            except:
                # logger.error(f'线程出错{traceback.format_exc()}')
                print(f'线程出错{traceback.format_exc()}')
                DISCONNECT = True
                time.sleep(2)
        print("hear已退出")

        # DISCONNECT = True
        # return False

    def receive_exact_length(self, length):
        received_data = b''  # 用于存储接收到的数据
        while len(received_data) < length:
            try:
                chunk = self.conn.recv(length - len(received_data))
                if not chunk:
                    # 如果 recv 返回空数据，表示连接已关闭或者发生了其他错误
                    raise ConnectionError("Connection closed prematurely.")
                received_data += chunk
            except ConnectionError as e:
                print(f"接收数据时发生错误: {e}")
                break  # 可以根据实际情况选择退出循环或者重新尝试连接
        return received_data

    def send(self, data):
        global DISCONNECT
        # print('进入发送线程')
        try:
            # print(Client.conn)
            self.conn.sendall(data)
            # print(f'客户端发送了数据: {data}')

        except:
            # logger.error(f'发送线程出错{traceback.format_exc()}')
            print(f'发送线程出错{traceback.format_exc()}')
            # print('连接断开')
            # DISCONNECT = True

    def send_heart(self):
        while True and not Client.break_sign:
            try:
                heart = DTK_fun1.SendData()
                heart_data = heart.heart()
                self.send(heart_data)
                # logger.info(f'向通道机发送心跳: {heart_data}')
                time.sleep(2)
            except:
                print(f'线程出错{traceback.format_exc()}')
        print('send_heart结束')


class RecvData:  # 报文接收类
    def __init__(self, conn):
        self.conn = conn

    def handle_recv(self, messages_queue):
        while True and not Client.break_sign:
            recv_data = messages_queue.get(timeout=15) # 10秒接收不到数据关闭
            data_type = recv_data['Type']
            if data_type == 1002:  # 读取反馈
                # logger.info(f'接收到读取反馈: {recv_data}')
                DTK_fun1.Status().back_1()
            elif data_type == 2001:  # 结果返回,发送反馈,存入mysql
                # logger.info(f'接收到结果返回: {recv_data}')
                packageID = recv_data['PackageId']
                barcode = recv_data['Barcode']
                back_data = DTK_fun1.SendData().read_feedback(packageID, barcode)  # 反馈报文
                self.conn.sendall(back_data)  # 发送反馈
                DTK_fun1.back_2(recv_data)


            elif data_type == 2003:  # 故障报告
                # logger.info(f'接收到故障报告: {recv_data}')
                print(f'接收到故障报告: {recv_data}')

            elif data_type == 0:  # 心跳
                pass
                # logger.info(f'接收到心跳: {recv_data}')
        print("handle_recv已退出 ")


if __name__ == '__main__':
    msg_queue = queue.Queue()
    cli = Client(msg_queue)
    cli.connect()
    c = threading.Thread(target=cli.run).start()
    sb = DTK_fun1.StartButton()
    x = sb.csv_proofread('41230001', cli)
