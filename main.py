# -*- coding: utf-8 -*-
import json
import time
import traceback
# import redis
from fLog import clsLogger
from fConfig import clsConfig
# import fRedis

class main:
    def __init__(self):
        # 仅初始化所有变量，禁止在此执行可能报错的语句
        __version__='0.1.0'
        
        # 定义线程总表，所有在该表格中的线程由main启动并监控
        self.lst_thread_name = ["HIKCamera", "PLC"]
        # self.user_list = []
        

    def run(self):
        ini_config=clsConfig('main.ini')        
        __inst_logger__ = clsLogger(ini_config)  
        #__inst_redis__ = clsRedis(ini_config)
        __inst_logger__.info("main 线程启动")
        # 读取配置文件，例如redis地址
        
        # log 配置文件读取成功/否则log 配置文件错误并退出主程序  
        try:
            ini_config2=clsConfig('main.ini')
        except:
        #    input("read redis info from ini failed, press any keys....")
            __inst_logger__.error("配置读取失败--Redis地址未能成功获取"+traceback.format_exc())
            input("从ini文件中读取Redis地址失败,请按任意键....")
            exit
        # 组合redis地址 端口与默认数据库至一个字符串，便于传递给各线程
        # redis_info= __redis_addr__+'/'+__redis_port__+'/'+__redis_db__
        # __device_name__= config['Name']['Device_Name']
        # 不再组合Redis地址信息机device name信息，直接将ini_config实例传递给各线程

        __inst_logger__.info("配置与日志初始化成功")
        

        # 尝试连接Redis
        try:
            #__inst_redis__.connect()
            #self.r = redis.Redis(host=__redis_addr__, port=__redis_port__, db=__redis_db__)
            #self.r.set(f"sys:device_name",__device_name__)
            time.sleep(10)
        except:
            __inst_logger__.error ("Redis链接失败"+traceback.format_exc())
            exit
        '''                
        # 按prc_list启动所有线程
        # 每启动一个现场，log一次，
        for str_prc_name in enumerate(lst_thread_name)
            if(prc_id=fProcess.start_process(str_prc_name))
               log('str_prc_name start as prc_id') 
            
        # 启动prc_monitor
        prc_id=fProcess.start_process('prc_mon')
        log('prc_mon start as prc_id') 
        
        self.r.set(f"sys:ready", "true")
        
        # while prc_mon run lock，循环;
        __loop_status__ = true;
        while __loop_status__:
           if self.r.get(f"prc_mon:run_lock") is not true;
               __loop_status__ = false;
           # Do Something;
           sleep(100)
        config = configparser.ConfigParser()
            config.read('main.ini')
            __redis_addr__ = config['Network']['Redis_IP']
            __redis_port__ = config['Network']['Redis_Port']
            __redis_db__ = config['Network']['Redis_db']
'''
     
if __name__ == '__main__':
    app = main()
    app.run()
