# prc_monitor
import time
import datetime

# from numpy.ma.extras import average
# from requests.packages import target

from include.fLog import clsLogger
from include.fConfig import clsConfig
# from include.fConfigEx import clsConfigEx
from include.fRedis import clsRedis
from prc.prc_HIKCamera import start_process as start_HIKCamera
from prc.prc_PLC import start_process as start_PLC
from prc.prc_stmHIKC_data import start_process as start_stmHIKC_data
from prc.prc_stmManualScan import start_process as start_stmManualScan
from prc.prc_stmReadingConfirm import start_process as start_stmReadingConfirm
from prc.prc_stmHIKC_file import start_process as start_stmHIKC_file
from prc.prc_BarcodeCheck import start_process as start_BarcodeCheck
from prc.prc_stmReadingConfirm_dss import start_process as start_stmReadingConfirm_dss

def start_process(config_file,lstThread):
    __prc_name__ = "monitor"

    ini_config = clsConfig(config_file)     # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)     # 实际上与主线程使用的是同一实例
    inst_redis = clsRedis(ini_config)       # 实际上与主线程使用的是同一实例

    inst_logger.info("线程 %s 正在启动" %(__prc_name__,))

    # 本地ini文件读取
    # str_ini_file_name = "prc_%s.ini" %(__prc_name__,)
    # __ini_prc_config__=clsConfigEx(str_ini_file_name)
    __prc_cycletime=ini_config.CycleTime.prc_monitor_cycletime
    __prc_expiretime=ini_config.CycleTime.prc_monitor_expiretime
    __prc_healthytime=ini_config.CycleTime.prc_monitor_healthytime
    # --------------------    
    # 定制化配置参数读取区

    # 定制化配置参数读取区
    # --------------------
   
    # 系统将初始化信息写入Redis
    __prc_id__ = inst_redis.init_prc(__prc_name__,__prc_expiretime)
    if not __prc_id__:  # 取得异常消息队列中的信息
        for i, e in enumerate(inst_redis.lstException):
            inst_logger.error(
                "线程 %s 注册 Redis 服务器失败，调用模块 %s，调用时间 %s，异常信息 %s "
                % (__prc_name__,e['module'], e['timestamp'], e['msg']))
        inst_redis.lstException.clear()
        return       # Redis 注册失败失败
    # --------------------    
    # 以下为定制初始化区域

    # 以上为定制初始化区域           
    # --------------------    


    b_thread_running = True
    int_exit_code = 0
    lst_thread_del =[]
    while b_thread_running:
       # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
        # --------------------
        # 以下为主线程操作区
        for i,th in enumerate(lstThread):
            if not th.is_alive():
                 inst_logger.error(f"prc_mon 检测到 %s 已退出"%(th.getName(),))
                 lst_thread_del.append(th)
        for i,th in enumerate(lst_thread_del):
            lstThread.remove(th)
            lst_thread_del.remove(th)
        

        # 以上为主线程操作区       
        # --------------------
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        
        # 线程运行时间与健康程度判断
        inst_redis.ct_refresh(__prc_name__)
        # ToDo
        
                
        # 线程是否继续运行的条件判断
        # 如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock = inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if (prc_run_lock is None) | (len(lstThread)==0) :
            int_exit_code = 1
            break

        # 如command区收到退出命令，根据线程类型决定是否立即退出
        prc_run_lock = inst_redis.getkey(f"pro_mon:{__prc_name__}:command")
        if prc_run_lock == "exit":
            # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
            # 如有则暂缓退出，如没有立即退出
            for i, th in enumerate(lstThread):
                inst_redis.setkey(f"pro_mon:%s:command"%(th.getName(),), "exit")
                inst_logger.info(f"set pro_mon:%s:command &=%s"%(th.getName(), "exit"))

            for i, th in enumerate(lstThread):
                th.join()
            int_exit_code = 2
            break

    inst_logger.info("线程 %s 已退出，返回代码为 %d" % (__prc_name__, int_exit_code))




