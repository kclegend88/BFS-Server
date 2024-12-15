# -*- coding: utf-8 -*-
import json
import time
import traceback
import threading
# import redis
from fLog import clsLogger
from fConfig import clsConfig
from fRedis import clsRedis

from prc_HIKCamera import start_process as start_HIKCamera
from prc_PLC import start_process as start_PLC

class main:
    def __init__(self):
        # 仅初始化所有变量，禁止在此执行可能报错的语句
        __version__='0.1.0'
        
        # 定义线程总表，所有在该表格中的线程由main启动并监控
        self.lst_thread_name = ["HIKCamera", "PLC"]
        

    def run(self):
        # 创建配置ini、log、redis实例
        ini_config=clsConfig('main.ini')        
        __inst_logger__ = clsLogger(ini_config)  
        __inst_redis__ = clsRedis(ini_config)
        
        __inst_logger__.info("main 线程启动")

        # 读取配置文件
        try:
            __device_name__= ini_config.Name.Device_Name
        except:
            __inst_logger__.error("配置读取失败"+traceback.format_exc())
            input("从ini文件中读取配置信息失败,请按任意键....")
            exit
        __inst_logger__.info("配置与日志初始化成功")

        # 尝试连接Redis
        try:
            __inst_redis__.connect(ini_config)
            __inst_redis__.setkey(f"sys:ready", "true")

            __inst_logger__.info("Redis 连接成功")
        except:
            __inst_logger__.error ("Redis连接失败"+traceback.format_exc())
            exit
        
        # 尝试启动线程
        str_thread_name=''
        try:
            # 遍历线程总表 逐个启动现场
            for i,str_prc_name in enumerate(self.lst_thread_name):
                # 每个线程的start_process 需在import中 定义为start_ + 线程名称
                str_thread_name = "start_%s" %(str_prc_name,)
                __inst_logger__.info("主程序尝试启动线程: %s" %(str_thread_name,))
                # 通过globlas().get 取得指定名称的入口句柄 返回给Thread作为线程启动入口
                thread = threading.Thread(target=globals().get(str_thread_name), args=(ini_config,),name=str_prc_name)
                thread.start()

            __inst_logger__.info("主程序已尝试启动全部线程，共计 %d 个" % (len(self.lst_thread_name),))
        except:
            __inst_logger__.error ("线程启动失败"+traceback.format_exc())
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
                    # 组合redis地址 端口与默认数据库至一个字符串，便于传递给各线程
        # redis_info= __redis_addr__+'/'+__redis_port__+'/'+__redis_db__
        # __device_name__= config['Name']['Device_Name']
        # 不再组合Redis地址信息机device name信息，直接将ini_config实例传递给各线程
'''
     
if __name__ == '__main__':
    app = main()
    app.run()
