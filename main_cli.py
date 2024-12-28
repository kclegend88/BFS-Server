# -*- coding: utf-8 -*-
import json
import time
import traceback
import threading
import sys
# import redis
from fLog import clsLogger
from fConfig import clsConfig
from fRedisEx import clsRedis

#from prc_stmP import start_process as start_stmP
#from prc_stmC import start_process as start_stmC
from prc_cli_manualscan import start_process as start_cli_manualscan

class main:
    def __init__(self):
        # 仅初始化所有变量，禁止在此执行可能报错的语句
        __version__='0.1.0'
        
        # 定义线程总表，所有在该表格中的线程由main启动并监控
        self.lst_thread_name = ["cli_manualscan"]
        

    def run(self):
        # 创建配置ini、log、redis实例
        ini_config = clsConfig('main_cli.ini')      ## 区别于main 函数, 每个cli用不同的config文件 ## 
        inst_logger = clsLogger(ini_config)
        inst_redis = clsRedis(ini_config)
        
        inst_logger.info("main_cli 线程启动")

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
            main_prc_running = inst_redis.getkey(f"sys:ready")      ## 取得服务器状态，如果服务器不在线则客户端退出
            if not main_prc_running == "true":
                # main线程尚未运行，强制退出
                inst_logger.error("主程序尚未启动，本程序将退出！！！")
                sys.exit(1)
            
            # cli客户端暂时不检查是否有客户端在运行 
            # cli_prc_running = inst_redis.getkey(f"sys_cli:ready")  
            # if cli_prc_running == "true":
            #    inst_logger.error("已有程序运行中，本程序将退出！！！")
            #    exit()
            # inst_redis.setkey(f"sys_cli:ready", "true")             ## 区别于main 函数, 每个cli用不同的sys:ready 键对值

            inst_logger.info("Redis 连接成功")
            
            ## inst_redis.flushall()                                ## 区别于main 函数, cli不允许清除数据
            ## inst_logger.info("Redis 数据清理成功")
            
        except:
            inst_logger.error("Redis连接失败"+traceback.format_exc())
            sys.exit(2)
        
        # 尝试启动线程
        # str_thread_name=''
        try:
            # 遍历线程总表 逐个启动线程
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
            sys.exit(3)
        
        # 退出时应清理主线程运行标志
        # inst_redis.setkey(f"sys_cli:ready", "false")
        #         
if __name__ == '__main__':
    app = main()
    app.run()
