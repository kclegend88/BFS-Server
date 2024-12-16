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
      
    def setkey(self, key, value):
        # 设置key-value 键对值
        if self.__isconnected__:
            self.decoded_connection.set(f"{key}", f"{value}")
        else:
            raise Exception("Redis尚未建立连接")
    
    def setkeypx(self, key, value, px):
        # 设置key-value 键对值，过期时间px ms
        if self.__isconnected__:
            self.decoded_connection.psetex(f"{key}", int(px), f"{value}")
        else:
            raise Exception("Redis尚未建立连接")
    
    def getkey(self, key):
        # 查询key-value 键对值
        if self.__isconnected__:
            value = self.decoded_connection.get(f"{key}")
            if value is None:
                # ToDo 后续为redis建立私有logger，查询到空键对值时logger.debug
                return None
            else:
                return value
        else:
            raise Exception("Redis尚未建立连接")
            
    def incrkey(self, key):
        # 增加键对值，并返回结果
        if self.__isconnected__:
            value = self.decoded_connection.incr(f"{key}")
            return int(value)
        else:
            raise Exception("Redis尚未建立连接")
            
    def lpush(self, name,value ):
        # 向列表左侧增加值
        # TODO 将该字函数做成自动控制lst长度，并返回平均值(或最大值)
        if self.__isconnected__:
            self.decoded_connection.lpush(f"{name}",f"{value}")
            return
        else:
            raise Exception("Redis尚未建立连接")
    
    def llen(self, name):
        # 取得列表长度
        if self.__isconnected__:
            value = self.decoded_connection.llen(f"{name}")
            return int(value)
        else:
            raise Exception("Redis尚未建立连接")
            
    def rpop(self, name):
        # 将列表最右侧元素压出
        if self.__isconnected__:
            self.decoded_connection.rpop(f"{name}")
            return
        else:
            raise Exception("Redis尚未建立连接")
                        
    def sadd(self, name, value ):
        # 向set增加值
        # TODO 返回是否有元素重复
        if self.__isconnected__:
            self.decoded_connection.sadd(name,value)
            return
        else:
            raise Exception("Redis尚未建立连接")
    
    def flushall(self):
        # 向set增加值
        # TODO 返回是否有元素重复
        if self.__isconnected__:
            self.decoded_connection.flushall()
            return
        else:
            raise Exception("Redis尚未建立连接")