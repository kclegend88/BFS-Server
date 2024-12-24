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
        self.ini_config = clsConfig(config_file)

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
            self.__isconnected__ = True
            return
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

    def lpush(self, name, value):
        # 向列表左侧增加值
        # TODO 将该字函数做成自动控制lst长度，并返回平均值(或最大值)
        if self.__isconnected__:
            self.decoded_connection.lpush(f"{name}", f"{value}")
            return
        else:
            raise Exception("Redis尚未建立连接")
    
    def lpush_ct(self, name , value ):
        # cycletime专用 lpush：向列表左侧增加值，自动判断长度，如果大于10向右rpop，自动返回ct平均值和最大值
        if self.__isconnected__:
            self.decoded_connection.lpush(f"{name}",f"{value}")
            int_len_lst =  self.decoded_connection.llen(f"{name}")
            if int_len_lst > 10:
                self.decoded_connection.rpop(f"{name}")
            lst_temp = self.decoded_connection.lrange(f"{name}",0,-1)
            int_sum_ct = 0
            int_max_ct = 0
            for item in lst_temp:
                int_sum_ct = int_sum_ct + int(item)
                if int(item) > int_max_ct:
                    int_max_ct = int(item)
            int_avg_ct = int(int_sum_ct/int_len_lst)
            # response['avg_ct'] = int_avg_ct
            # response['max_ct'] = int_max_ct
            # response['msg'] = 'OK'
            # response['code'] = 200
            # return response
            return int_avg_ct
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

    def sadd(self, name, value):
        # 向set增加值
        # TODO 返回是否有元素重复
        if self.__isconnected__:
            self.decoded_connection.sadd(name, value)
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
    def xadd(self, name, value ):
        # 向stream增加值
        # TODO 返回是否有元素重复
        if self.__isconnected__:
            self.decoded_connection.xadd (name,value)
            return
        else:
            raise Exception("Redis尚未建立连接")
 
    def xread_one(self, name):
        # 从stream读取1条
        if self.__isconnected__:
            response = self.decoded_connection.xread (count=1,streams={f"{name}":0})
            return response
        else:
            raise Exception("Redis尚未建立连接")   
 
    def xread_all(self, name):
        # 从stream读取所有
        if self.__isconnected__:
            response = self.decoded_connection.xread (streams={f"{name}":0})
            # xread 返回值解析
            # 后续加入结构和流解析模块，返回解析后的数值
            # [
            #  [stream_name, 
            #   [
            #    (redis_id1,{'id': '0', 'msg': 'ok', 'addr': 'abc'}), 
            #    (redis_id2,{'id': '1', 'msg': 'ok', 'addr': 'abc'}),
            #    (redis_id3,{'id': '1', 'msg': 'ok', 'addr': 'abc'})
            #   ]
            #  ]
            # ]
            # len(response)= 1:     streams的数量
            # len(response[0]) =2   第一个streams 回复的信息，信息一定有两列组成
            #       response[0][0] = stream_name 
            #       response[0][1] = all_msg
            # len(response[0][1]) = 3 信息的总行数( for index = 0~2 )
            #   for id, value in l[0][1]:  print( f"id: {id} value: {value[b'msg']}")
            #   id: b'redis_id1' value: b'OK'
            #   id: b'redis_id2' value: b'OK'
            #   id: b'redis_id3' value: b'OK'
            #       response[0][1][0] = (redis_id1,{'id': '0', 'msg': 'ok', 'addr': 'abc'})
            #       response[0][1][1] = (redis_id2,{'id': '1', 'msg': 'ok', 'addr': 'abc'})
            #       response[0][1][2] = (redis_id3,{'id': '1', 'msg': 'ok', 'addr': 'abc'})
            # len(response[0][1][index]) = 2 每条信息都包含 Redis id 和信息本体 两部分
            #       response[0][1][index][0] = redis_id1 
            #       response[0][1][index][1] = {'id': '0', 'msg': 'ok', 'addr': 'abc'}
            #       data_decoded = {key.decode(): value.decode() for key, value in response[0][1].items()}
            # len(response[0][1][index][1]) = 3 信息本体中 包含的键值数量( for key =  )
            # 
            # response = self.decoded_connection.xread (count=1, streams={f"{name}":0})
            # print(response)
            # response = self.decoded_connection.xread ({"f{name}":"0-0"})
            return response
        else:
            raise Exception("Redis尚未建立连接")   

    def xdel_one(self, name, msg_id):
        # 从stream中删除1条
        if self.__isconnected__:
            response = self.decoded_connection.xdel (name,msg_id)
            return response
        else:
            raise Exception("Redis尚未建立连接") 
          
    def xcreategroup(self, sname, gname):
        # 为每个线程创建一个组
        if self.__isconnected__:
            self.decoded_connection.xgroup_create (sname,gname, id=0)
            return 
        else:
            raise Exception("Redis尚未建立连接")         
    
    def xreadgroup(self, sname,gname,cname):
        # 使用组读取
        if self.__isconnected__:
            response= self.decoded_connection.xreadgroup (groupname=gname,consumername = cname,count=1,streams={f"{sname}":'>'})
            return response
        else:
            raise Exception("Redis尚未建立连接")    
            
    def xack(self, sname,gname,sid):
        # 使用组读取
        if self.__isconnected__:
            response= self.decoded_connection.xack(sname,gname,sid)
            return response
        else:
            raise Exception("Redis尚未建立连接")    



    def clearkey(self, key):
       # 清除键对
        if self.__isconnected__:
            self.decoded_connection.delete(f"{key}")
            return
        else:
            raise Exception("Redis尚未建立连接")
 
    def getset(self, key):
        # 获取集合
        if self.__isconnected__:
            value = self.decoded_connection.smembers(f"{key}")
            return value
        else:
            raise Exception("Redis尚未建立连接")