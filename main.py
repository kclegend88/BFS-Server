# -*- coding: utf-8 -*-
import configparser
import json
import time
import traceback
import redis
# import fRedis

class main:
    def __init__(self):
        # 仅初始化所有变量，禁止在此执行可能报错的语句
        __version__='0.1.0'
        
        # 定义线程总表，所有在该表格中的线程由main启动并监控
        self.lst_thread_name = ["HIKCamera", "PLC"]
        # self.user_list = []
        

    def run(self):
        # log : main线程启动 
                
        # 读取配置文件，例如redis地址
        # log 配置文件读取成功/否则log 配置文件错误并退出主程序  
        try:
            config = configparser.ConfigParser()
            config.read('main.ini')
            __redis_addr__ = config['Network']['Redis_IP']
            __redis_port__ = config['Network']['Redis_Port']
            __redis_db__ = config['Network']['Redis_db']
            
        except:
        #    log ("配置读取失败--Redis 地址未能成功获取")
        #    log traceback.format_exc()
        #    input("read redis info from ini failed, press any keys....")
            input("从ini文件中读取Redis地址失败,请按任意键....")
            exit
        # 组合redis地址 端口与默认数据库至一个字符串，便于传递给各线程
        redis_info= __redis_addr__+'/'+__redis_port__+'/'+__redis_db__
        
        __device_name__= config['Name']['Device_Name']
        
        # 尝试连接Redis
        try:
            self.r = redis.Redis(host=__redis_addr__, port=__redis_port__, db=__redis_db__)
            self.r.set(f"sys:device_name",__device_name__)
            
        except:
            log ("Redis链接失败")
            log traceback.format_exc()
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
        '''
 
if __name__ == '__main__':
    app = main()
    app.run()
