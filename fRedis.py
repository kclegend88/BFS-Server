# -*- coding: utf-8 -*-

import redis
from fConfig import clsConfig


class clsRedis:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(clsRedis, cls).__new__(cls)
            cls._instance.init(*args, **kwargs)
        return cls._instance

    def init(self, config_file):
        self.ini_config=clsConfig(config_file)


    def connect(self, config_file):
        # 从配置文件中 读取Redis信息
        self.__redis_addr__ = self.ini_config.Network.Redis_IP
        self.__redis_port__ = self.ini_config.Network.Redis_Port
        self.__redis_db__ = self.ini_config.Network.Redis_db
        
        # self.__inst_redis__ = redis.Redis(host=__redis_addr__, port=__redis_port__, db=__redis_db__)
        
        # 使用默认方式连接本地Redis
        # ToDo 当前未使用配置文件中的IP与端口，也未处理配置文件中上述信息缺失可能导致的异常退出
        # ToDo 当Redis连接出现异常时，Redis是否自动重新连接尚未有结论，重连机制是否需要主线程参与需要详细测试后得出结论
        self.decoded_connection = redis.Redis(decode_responses=True)
        if self.decoded_connection.ping():
            self.__isconnected__ = True ;
            return;
        else:
            raise Exception("无法连接到Redis默认主机")
      
    def setkey(self, key,value):
        # 设置key-value 键对值
        if self.__isconnected__:
            self.decoded_connection.set(f"sys:ready", "true")
        else:
            raise Exception("Redis尚未建立连接")

