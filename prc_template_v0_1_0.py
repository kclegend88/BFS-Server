# prc_template  v 0.1.0
import time
from fLog import clsLogger
from fConfig import clsConfig
from fRedis import clsRedis

def start_process(config_file):
    __prc_name__="xxxx"
    
    ini_config=clsConfig(config_file)        
    __inst_logger__ = clsLogger(ini_config)  
    __inst_redis__ = clsRedis(ini_config)
    
    __inst_logger__.info("线程 %s 正在启动" %(__prc_name__,))
    time.sleep(5)
    '''
    r = redis.Redis(host='127.0.0.1', port=6379, db=0)
    value = r.get(name)
    value_str = value.decode('utf-8')
    parsed_value = json.loads(value_str)
    parsed_value[0]['runStatus'] = 1
    # 将修改后的 Python 对象重新编码为 JSON 字符串
    updated_value_str = json.dumps(parsed_value)
    # 将修改后的值存回 Redis
    r.set(name, updated_value_str)
    print("HK线程状态修改成功")
    # 读取配置文件
    config = configparser.ConfigParser()
    config.read('prc_HIKCamera.ini')
    print("连接相机中")
    '''
    __inst_logger__.info("线程 %s 启动完成" %(__prc_name__,))


