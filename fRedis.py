# -*- coding: utf-8 -*-

import redis
from fConfig import clsConfig
import datetime
import threading
import traceback

class clsRedis:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(clsRedis, cls).__new__(cls)
            cls._instance.init(*args, **kwargs)
        return cls._instance

    def init(self, config_file):
        self.ini_config = clsConfig(config_file)
        self.__isconnected__ = False
        self.lstException = []          # 用于记录异常的清单
        self.dictKeyBuffer = {}         # 通过set key 的所有历史数据，均会建立buf，直到clear key, 使用setkeypx不会建立buf, 使用getkeys_frombuf时返回全部缓存的key，或prefix=""中指定的前缀下所有的key
        self.redis_lock = threading.Lock()
        self.dictPrcLuts = {}
        
    def append_exception(self, subfunc, msg):
        self.lstException.append(
            {'module': f'clsRedis.{subfunc}',
             'timestamp': datetime.datetime.now().isoformat(),
             'msg': msg})
    def connect(self, config_file):
        if self.__isconnected__:
            return
        
        # 从配置文件中 读取Redis信息
        self.__redis_addr__ = self.ini_config.Network.Redis_IP
        self.__redis_port__ = self.ini_config.Network.Redis_Port
        self.__redis_db__ = self.ini_config.Network.Redis_db
        
        # 连接至Redis
        try:
            print(f"尝试连接 ip={self.__redis_addr__},port={self.__redis_port__},db={self.__redis_db__}")
            #self.decoded_connection = redis.Redis(decode_responses=True)
            self.decoded_connection = redis.Redis(host=self.__redis_addr__,
                                                  port=self.__redis_port__,
                                                  db=self.__redis_db__,decode_responses=True)
            if self.decoded_connection.ping():
                self.__isconnected__ = True
                return
            else:
                self.append_exception("connect", "连接后无响应")
        except Exception as e:
            self.append_exception("connect", "连接失败:%s"%(traceback.format_exc(),))
    def getkey(self, key):      # 查询key-value 键对值
        with self.redis_lock:                   # 对Redis的读写线程加锁
            try:
                if self.__isconnected__:        # 确认连接状态
                    value = self.decoded_connection.get(f"{key}")
                    if value is None:           # Redis返回空值,说明key不存在
                        self.append_exception("getkey", "未创建的key:%s"%(traceback.format_exc(),))
                        return None
                    else:
                        return value
                else:                           # 返回未连接错误
                    self.append_exception("getkey", "Redis未连接")
            except Exception as e:
                self.append_exception("getkey","读取key:%s 时发生异常:%s"%(key,traceback.format_exc()))
    def setkey(self, key, value):               # 设置key-value 键对值
        with self.redis_lock:                   # 对Redis的读写线程加锁
            try:
                if self.__isconnected__:        # 确认连接状态
                    if not key in self.dictKeyBuffer:
                        pass                    #  ToDo 后续为创建key增加记录，增加计数，增加index,增加set get和旧键值比较功能
                    self.dictKeyBuffer[f"{key}"] = f"{value}"
                    self.decoded_connection.set(f"{key}", f"{value}")
                    return
                else:                           # 返回未连接错误
                    self.append_exception("setkey", "Redis未连接")
            except Exception as e:
                self.append_exception("setkey", "写入key:%s 时发生异常:%s"%(key,traceback.format_exc()))
    def clearkey(self, key):        # 删除key-value 键对值
        with self.redis_lock:                   # 对Redis的读写线程加锁
            try:
                if self.__isconnected__:        # 确认连接状态
                    if not key in self.dictKeyBuffer:
                        self.append_exception("getkey", "读取key:%s 时发生异常:%s" % (key, traceback.format_exc()))
                        self.append_exception("clearkey", "尝试删除一个不存在的key")
                        return None
                    else:
                        value = self.dictKeyBuffer.pop(f"{key}",None)
                        self.decoded_connection.delete(f"{key}")
                        return value
                else:                           # 返回未连接错误
                    self.append_exception("clearkey", "Redis未连接")
                    return None
            except Exception as e:
                self.append_exception("setkey", "清除key:%s 时发生异常:%s" % (key, traceback.format_exc()))
                return None
    def setkeypx(self, key, value, px):    # 设置key-value 键对值，过期时间px ms
        try:
            if self.__isconnected__:        # 确认连接状态
                self.decoded_connection.psetex(f"{key}", int(px), f"{value}")
                return
            else:                        # 返回未连接错误
                self.append_exception("setkeypx", "Redis未连接")
                return None
        except Exception as e:
            self.append_exception("setkeypx", "写入key:%s 时发生异常，px= %d , %s"%(key, int(px), traceback.format_exc()))
            return None
    def init_prc(self, prc_name, prc_expiretime):
        # 向Redis注册基本信息
        prc_run_lock = self.getkey(f"pro_mon:{prc_name}:run_lock")
        if prc_run_lock is None:
            # Redis中不存在该线程的运行锁，说明没有同名线程正在运行，无线程冲突，可以开始初始化
            # 增加Redis中总线程计数器，并将增加后的计数器值作为当前线程的id
            prc_id = self.incrkey(f"pro_mon:prc_counter")
            # inst_logger.info("线程 %s 取得 id = %d" % (__prc_name__, __prc_id__))
            self.setkeypx(f"pro_mon:{prc_name}:run_lock", prc_id, prc_expiretime)
            #inst_logger.info("线程 %s 已设置线程锁，过期时间 = %d ms" % (__prc_name__, __prc_expiretime))

            # 增加当前线程的重启次数,如为1说明是首次启动
            __prc_restart__ = self.incrkey(f"pro_mon:{prc_name}:restart")
            # inst_logger.info("线程 %s 启动次数 restart = %d" % (__prc_name__, __prc_restart__))

            # 记录线程启动时间
            __prc_start_ts__ = datetime.datetime.now()
            self.setkey(f"pro_mon:{prc_name}:start_ts", __prc_start_ts__.isoformat())
            #inst_logger.info("线程 %s 启动时间 start_ts= %s" % (__prc_name__, __prc_start_ts__.isoformat()))

            # 记录线程上次刷新时间，用于持续计算线程的cycletime
            prc_luts = __prc_start_ts__
            self.setkey(f"pro_mon:{prc_name}:lu_ts", prc_luts.isoformat())
            self.dictPrcLuts[prc_name] = prc_luts

            # 将当前线程加入Redis 线程集合中
            self.sadd("set_process", "name=%s/id=%d" % (prc_name, prc_id))
            #inst_logger.info("线程 %s 已添加至线程集合中" % (__prc_name__,))
            return prc_id
        else:
            # Redis中存在该线程的运行锁，说明已经有同名线程正在运行
            # 记录线程冲突错误并退出
            # inst_logger.error("线程 %s 启动时发现了运行冲突,同名线程已存在,id= %d" % (__prc_name__, prc_run_lock))
            self.append_exception("init_prc",f"初始化{prc_name}时发生错误")
            return None
    def ct_refresh(self,prc_name):
        current_ts = datetime.datetime.now()
        td_last_ct = current_ts - self.dictPrcLuts[prc_name]  # datetime对象相减得到timedelta对象
        int_last_ct_ms = int(td_last_ct.total_seconds() * 1000)  # 取得毫秒数（int格式)

        self.dictPrcLuts[prc_name] = current_ts  # 刷新luts
        self.setkey(f"pro_mon:{prc_name}:lu_ts", current_ts.isoformat())  # 更新redis中的luts

        self.lpush(f"lst_ct:%s" % (prc_name,), int_last_ct_ms)  # 将最新的ct插入redis中的lst_ct
        int_len_lst = self.llen(f"lst_ct:%s" % (prc_name,))  # 取得列表中元素的个数
        if int_len_lst > 10:
            self.rpop(f"lst_ct:%s" % (prc_name,))  # 尾部数据弹出
        # cycletime 计算 与 healthy判断
        return
    def keysbuf(self,prefix):
        lst_result=[]
        for i, key in enumerate(self.dictKeyBuffer):
            if key.startswith(prefix):
                lst_result.append(key)
        if lst_result:
            return lst_result
        else:
            return None

    def incrkey(self, key , incrby = 1):
        # 增加键对值，并返回结果
        if self.__isconnected__:
            value = self.decoded_connection.incrby(f"{key}",incrby)
            return int(value)
        else:
            raise Exception("Redis尚未建立连接")

    
    def keys(self, prefix):
        # 查询key-value 键对值
        if self.__isconnected__:
            value = self.decoded_connection.scan(match=f"{prefix}*",count = 100)
            if value[1] is None:
                # ToDo 后续为redis建立私有logger，查询到空键对值时logger.debug
                return None
            else:
                result = value[1].copy()
                while not int(value[0]) == 0:
                    value=self.decoded_connection.scan(cousor=value[0],match=f"{prefix}*",count = 100)
                    result.append(value[1].copy())
                return result
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
        # cycletime专用 lpush：向列表左侧增加值，自动判断长度，如果大于10向右rpop，自动返回ct平均值、最大值
        response = {}
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
            response['avg_ct'] = int_avg_ct
            response['max_ct'] = int_max_ct
            response['msg'] = 'OK'
            response['code'] = 200
            return response
            # return int_avg_ct
        else:
            # raise Exception("Redis尚未建立连接")
            return None
    
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
            self.decoded_connection.xgroup_create (sname,gname, id=0, mkstream=True)
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


    def clearset(self, key):
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