# -*- coding: utf-8 -*-
import json
import time
import traceback
import threading
import sys
from typing import final

# import redis
from fLog import clsLogger
from fConfig import clsConfig
from fRedis import clsRedis

#from prc_stmP import start_process as start_stmP
#from prc_stmC import start_process as start_stmC
from prc_HIKCamera import start_process as start_HIKCamera
from prc_PLC import start_process as start_PLC
from prc_stmHIKC_data import start_process as start_stmHIKC_data
from prc_stmManualScan import start_process as start_stmManualScan
from prc_stmReadingConfirm import start_process as start_stmReadingConfirm

class main:
    def __init__(self):
        # 仅初始化所有变量，禁止在此执行可能报错的语句
        self.__version__='0.1.0'
        self.status = 127       # 初创建 状态为 127
        # 定义线程总表，所有在该表格中的线程由main启动并监控
        self.lst_thread_name = ["HIKCamera","stmHIKC_data","stmReadingConfirm","stmManualScan","PLC"]
#        self.lst_thread_name = ["HIKCamera","stmHIKC_data","stmReadingConfirm","stmManualScan"]
        

    def run(self):
        # 创建配置ini、log、redis实例
        ini_config = clsConfig('main.ini')
        self.inst_logger = clsLogger(ini_config)
        self.inst_redis = clsRedis(ini_config)
        
        self.inst_logger.info("main 线程启动")

        # 读取配置文件
        try:
            __device_name__= ini_config.Name.Device_Name
        except:
            self.inst_logger.error("配置读取失败"+traceback.format_exc())
            input("从ini文件中读取配置信息失败,请按任意键....")
            sys.exit(127)               # 无配置文件退出
        self.status = 126  # 读取配置文件成功，状态为 126
        self.inst_logger.info("配置与日志初始化成功")

        # 尝试连接Redis
        try:
            self.inst_redis.connect(ini_config)
            if self.inst_redis.lstException:  # 取得异常消息队列中的信息
                for i, e in enumerate(self.inst_redis.lstException):
                    self.inst_logger.error(
                        "主线程连接 Redis 服务器失败，调用模块 %s，调用时间 %s，异常信息 %s "
                        % (e['module'], e['timestamp'], e['msg']))
                self.inst_redis.lstException.clear()
                sys.exit(126)               # Redis 连接失败

            main_prc_running = self.inst_redis.getkey(f"sys:ready")
            if main_prc_running == "true":
                # 其他main线程正在运行中，强制退出
                self.inst_logger.error("已有程序运行中，本程序将退出！！！")
                sys.exit(126)           # 有实例运行导致退出

            self.inst_logger.info("Redis 连接成功")
            self.status = 125  # Redis 连接成功，状态为 125

            self.inst_redis.flushall()                   # 清理全部数据
            self.inst_logger.info("Redis 数据清理成功")
            self.status = 124  # Redis 数据清理成功，状态为 124

        except Exception as e:
            self.inst_logger.error("Redis连接失败"+traceback.format_exc())
            sys.exit(125)               # Redis 连接失败，或数据初始化失败
        
        self.inst_redis.setkey(f"sys:ready", "true") # 向Redis标注主程序已运行
        self.status = 123  # Redis 数据清理成功，状态为 124
        # 尝试启动线程
        try:
            # 遍历线程总表 逐个启动线程
            for i,str_prc_name in enumerate(self.lst_thread_name):
                str_thread_name = "start_%s" %(str_prc_name,)               # 每个线程的start_process 需在import中 定义为start_ + 线程名称
                self.inst_logger.info("主程序尝试启动线程: %s" %(str_thread_name,)) # 通过globlas().get 取得指定名称的入口句柄 返回给Thread作为线程启动入口
                thread = threading.Thread(target=globals().get(str_thread_name), args=(ini_config,),name=str_prc_name)
                thread.start()
                time.sleep(1)
            self.inst_logger.info("主程序已尝试启动全部线程，共计 %d 个" % (len(self.lst_thread_name),))
            self.status = 100  # 全部线程已通知启动，状态为 100
        except Exception as e:
            self.inst_logger.error ("线程启动失败"+traceback.format_exc())
            sys.exit(124)               # 启动线程时发生异常

    def __del__(self):
        # 退出时应清理主线程运行标志
        if self.status < 123:
            self.inst_redis.setkey(f"sys:ready", "false")

if __name__ == '__main__':
    app = main()
    try:
        app.run()
    except SystemExit as msg:
        print(traceback.format_exc())
        int_exit_code =int(str(msg))
    except Exception as e:
        print("其他异常")
        print(e)
    finally:
        input("press any key...")

