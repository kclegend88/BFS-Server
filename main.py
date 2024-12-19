# -*- coding: utf-8 -*-
import json
import time
import traceback
import threading
# import redis
from fLog import clsLogger
from fConfig import clsConfig
from fRedis import clsRedis

from prc_stmP import start_process as start_stmP
from prc_stmC import start_process as start_stmC

class main:
    def __init__(self):
        # 仅初始化所有变量，禁止在此执行可能报错的语句
        __version__='0.1.0'
        
        # 定义线程总表，所有在该表格中的线程由main启动并监控
        self.lst_thread_name = ["stmP", "stmC"]
        

    def run(self):
        # 创建配置ini、log、redis实例
        ini_config = clsConfig('main.ini')
        inst_logger = clsLogger(ini_config)
        inst_redis = clsRedis(ini_config)
        
        inst_logger.info("main 线程启动")

        # 读取配置文件
        try:
            __device_name__= ini_config.Name.Device_Name
        except:
            inst_logger.error("配置读取失败"+traceback.format_exc())
            input("从ini文件中读取配置信息失败,请按任意键....")
            exit()
        inst_logger.info("配置与日志初始化成功")

        # 尝试连接Redis
        try:
            inst_redis.connect(ini_config)
            
            main_prc_running = inst_redis.getkey(f"sys:ready")
            if main_prc_running == "true":
                # 其他main线程正在运行中，强制退出
                inst_logger.error("已有程序运行中，本程序将退出！！！")
                exit()
            
            inst_redis.setkey(f"sys:ready", "true")

            inst_logger.info("Redis 连接成功")
            
            inst_redis.flushall()
            inst_logger.info("Redis 数据清理成功")
            
        except:
            inst_logger.error ("Redis连接失败"+traceback.format_exc())
            exit()
        
        # 尝试启动线程
        # str_thread_name=''
        try:
            # 遍历线程总表 逐个启动现场
            for i,str_prc_name in enumerate(self.lst_thread_name):
                # 每个线程的start_process 需在import中 定义为start_ + 线程名称
                str_thread_name = "start_%s" %(str_prc_name,)
                inst_logger.info("主程序尝试启动线程: %s" %(str_thread_name,))
                # 通过globlas().get 取得指定名称的入口句柄 返回给Thread作为线程启动入口
                thread = threading.Thread(target=globals().get(str_thread_name), args=(ini_config,),name=str_prc_name)
                thread.start()
                time.sleep(1)

            inst_logger.info("主程序已尝试启动全部线程，共计 %d 个" % (len(self.lst_thread_name),))
        except:
            inst_logger.error ("线程启动失败"+traceback.format_exc())
            exit()
        
        # 退出时应清理主线程运行标志
        # inst_redis.setkey(f"sys:ready", "false")
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
