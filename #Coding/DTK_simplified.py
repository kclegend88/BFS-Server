# DTK_simplified.py
import socket
import json
import threading
import time


class ChannelClient:
    def __init__(self, server_ip, server_port, on_receive_callback=None):
        self.addr = (server_ip, server_port)
        self.conn = None
        self.is_connected = False
        self.heartbeat_interval = 5
        self.on_receive = on_receive_callback  # 接收数据的回调函数
        self._running = False

    def connect(self):
        """建立连接并自动重试"""
        while not self.is_connected:
            try:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect(self.addr)
                self.is_connected = True
                print(f"Connected to {self.addr}")
                self._start_threads()
            except Exception as e:
                print(f"Connection failed: {e}, retrying...")
                time.sleep(2)

    def _start_threads(self):
        """启动心跳和接收线程"""
        self._running = True
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        threading.Thread(target=self._receive_loop, daemon=True).start()

    def _heartbeat_loop(self):
        """心跳维持线程"""
        while self._running:
            try:
                self.send_heartbeat()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                print(f"Heartbeat error: {e}")
                self.is_connected = False
                self.connect()  # 尝试重连

    def _receive_loop(self):
        """数据接收线程"""
        while self._running and self.is_connected:
            try:
                data = self._receive_data()
                if data and self.on_receive:
                    self.on_receive(data)  # 触发回调处理
            except Exception as e:
                print(f"Receive error: {e}")
                self.is_connected = False

    def _receive_data(self):
        """接收并解析数据帧（示例格式：0x02 + 长度 + JSON + 0x03）"""
        header = self.conn.recv(1)
        if header != b'\x02':
            return None

        length_bytes = self.conn.recv(4)
        length = int.from_bytes(length_bytes, 'big')
        json_data = self.conn.recv(length)
        footer = self.conn.recv(1)

        if footer == b'\x03':
            return json.loads(json_data.decode())
        return None

    def send(self, data_type, barcode="", qty=0):
        """发送指令的统一接口"""
        packet = self._build_packet(data_type, barcode, qty)
        print(f"Sending packet: {packet}")
        try:
            self.conn.sendall(packet)
        except Exception as e:
            print(f"Send error: {e}")
            self.is_connected = False

    def _build_packet(self, data_type, barcode, qty):
        """构建报文（示例结构）"""
        data = {
            "Type": data_type,
            "Barcode": barcode,
            "Qty": qty,
            "Timestamp": time.time()
        }
        json_str = json.dumps(data).encode()
        return b'\x02' + len(json_str).to_bytes(4, 'big') + json_str + b'\x03'

    def send_heartbeat(self):
        """发送心跳包"""
        self.send(data_type=9001)

    def close(self):
        """关闭连接"""
        self._running = False
        self.conn.close()
        self.is_connected = False
# 回调函数处理接收数据
def handle_received_data(data):
    if data['Type'] == 2001:
        print("Received result:", data)
    elif data['Type'] == 2003:
        print("Received error report:", data)

if __name__ == '__main__':
    # 初始化客户端
    client = ChannelClient("127.0.0.1", 3000, on_receive_callback=handle_received_data)
    client.connect()
    time.sleep(2)
    # 发送读取请求
    client.send(data_type=1001, barcode="ABC123", qty=50)
    time.sleep(5)