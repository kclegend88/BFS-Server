# -*- coding: utf-8 -*-
import sys
sys.path.append("..")
sys.path.append("include")
import json
import time
import traceback
import threading
import sys
# import redis
from fLog import clsLogger
from fConfig import clsConfig
from fRedis import clsRedis


#from prc_stmP import start_process as start_stmP
#from prc_stmC import start_process as start_stmC
from prc_cli_manualscan import start_process as start_cli_manualscan
from prc_cli_playsound import start_process as start_cli_playsound
from main_cli_qt import start_process as start_cli_qt


class main:
    def __init__(self):
        # 仅初始化所有变量，禁止在此执行可能报错的语句
        __version__='0.1.0'
        
        # 定义线程总表，所有在该表格中的线程由main启动并监控
        self.lst_thread_name = ["cli_manualscan","cli_playsound", "cli_qt"]
        

    def run(self):
        # 创建配置ini、log、redis实例
        ini_config = clsConfig('main_cli.ini')      ## 使用客户端专用ini文件
        inst_logger = clsLogger(ini_config)
        inst_redis = clsRedis(ini_config)
        
        inst_logger.info("main_cli 线程启动")

        # 读取配置文件
        try:
            __device_name__= ini_config.Name.Device_Name
        except:
            inst_logger.error("配置读取失败"+traceback.format_exc())
            input("从ini文件中读取配置信息失败,请按任意键....")
            sys.exit(127)               # 无配置文件退出
        self.status = 126  # 读取配置文件成功，状态为 126
        inst_logger.info("配置与日志初始化成功")

        # 尝试连接Redis
        try:
            inst_redis.connect(ini_config)
            main_prc_running = inst_redis.getkey(f"sys:ready")      ## 取得服务器状态，如果服务器不在线则客户端退出
            if not main_prc_running == "true":
                # main线程尚未运行，强制退出
                inst_logger.error("主程序尚未启动，本程序将退出！！！")
                sys.exit(126)           # 主程序尚未启动导致退出

            self.status = 125  # 确认主线程成功启动，状态为 125
            # 向Redis注册基本信息，允许多个客户端，每个客户端同名线程只能有一个
            # main_cli向Redis申请唯一的cli_id，同一客户端不同线程之间使用cli_id连辨识消息是否是发给自己的
            cli_prc_running = inst_redis.getkey(f"sys_cli00:ready") # 取得 00 号客户端的 单实例运行锁
            index = 0
            if cli_prc_running:         # 如果已存在，递增cli id 寻找下一个可用的
                while cli_prc_running:
                    index = index + 1
                    if index > 90:       # cli_id最大 90
                        inst_logger.error("客户端启动时发现了过多客户端同时在运行，退出！")
                        sys.exit(125)
                    cli_prc_running=inst_redis.getkey(f"sys_cli%02d:ready"%(index,))
                    self.status = 124  # 取得cli id，状态为 124
            __cli_id__ = index
            inst_redis.setkey(f"sys_cli%02d:ready"%(__cli_id__,),"ready")
            inst_logger.info("Redis 连接成功")
        except:
            inst_logger.error("Redis连接失败"+traceback.format_exc())
            sys.exit(125)               # Redis 连接失败，或数据初始化失败

        lst_thread =[]
        # 尝试启动线程
        try:
            # 遍历线程总表 逐个启动线程
            for i,str_prc_name in enumerate(self.lst_thread_name):
                # 每个线程的start_process 需在import中 定义为start_ + 线程名称
                str_thread_name = "start_%s" %(str_prc_name,)
                inst_logger.info("主程序尝试启动线程: %s" %(str_thread_name,))
                # 通过globlas().get 取得指定名称的入口句柄 返回给Thread作为线程启动入口
                thread = threading.Thread(target=globals().get(str_thread_name), args=(ini_config,__cli_id__),name=str_prc_name)
                thread.start()
                lst_thread.append(thread)  # 加入线程列表
                time.sleep(1)

            inst_logger.info("主程序已尝试启动全部线程，共计 %d 个" % (len(self.lst_thread_name),))
        except:
            inst_logger.error ("线程启动失败"+traceback.format_exc())
            sys.exit(124)               # 启动线程时发生异常

        self.status = 100  # 全部线程已通知启动，状态为 100

        # 打印所有线程名称
        for i,th in enumerate(lst_thread):
            print(th.getName())

        while True:
            strInput = input("Type 'Y' and press enter if you want to exit...: ")
            if strInput == 'Y':
                break
            time.sleep(1)
            server_exit = inst_redis.getkey(f"sys_cli%02d:ready"%(__cli_id__,))
            if not server_exit:     # 主线程退出的时候 需要删除所有client的ready 信号
                break               # 主线程删除ready信号之后，client自动退出

        inst_redis.setkey(f"sys:cli%02d:command"%(__cli_id__,),"exit")
        # 将主程序堵塞至所有线程全部完成
        for i, th in enumerate(lst_thread):
            if th.getName()== "cli_qt":
                continue
            th.join()

        inst_redis.clearkey(f"sys:cli%02d:ready"%(__cli_id__,))
        inst_redis.clearkey(f"sys:cli%02d:command"%(__cli_id__,))
        inst_logger.info(f"sys_cli%02d:ready 已清除"%(__cli_id__,))

if __name__ == '__main__':
    app = main()
    try:
        app.run()
        print("所有线程已正常退出")
    except SystemExit as msg:
        print(traceback.format_exc())
        #if app.status < 125:    # 清理单一实例锁
        #    app.inst_redis.setkey(f"sys:ready", "false")
        #    app.inst_logger.info("sys_clixx:ready 已清除, sys status = %d"%(app.status,))
    except Exception as e:
        print("其他异常")
        print(e)
    finally:
        input("press any key...")