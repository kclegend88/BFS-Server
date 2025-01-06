# prc_template  v 0.2.0
import time
import datetime
from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis
import ast
import sqlite3

def start_process(config_file):
    __prc_name__="stmReadingConfirm"
    
    ini_config = clsConfig(config_file)   # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)  
    inst_redis = clsRedis(ini_config)
    inst_logger.info("线程 %s 正在启动" %(__prc_name__,))
    
    # 本地ini文件存储的本线程专有配置参数

    # 定义线程循环时间、过期时间、健康时间等
    str_ini_file_name = "prc_%s.ini" %(__prc_name__,)
    __ini_prc_config__=clsConfigEx(str_ini_file_name)
    
    __prc_cycletime=__ini_prc_config__.CycleTime.prc_cycletime
    __prc_expiretime=__ini_prc_config__.CycleTime.prc_expiretime
    __prc_healthytime=__ini_prc_config__.CycleTime.prc_healthytime
    

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
    
    if not inst_redis.xcreategroup("stream_reading_confirm", "ReadingConfirm"):
        inst_logger.info("线程 %s 注册stream组失败，该组已存在" %("ReadingConfirm",))
    else:
        inst_logger.info("线程 %s 注册stream组成功" %("ReadingConfirm",))
    
    b_thread_running = True
    int_exit_code = 0
    
    dictdata=[]
    lstdictdata={}
    conn = sqlite3.connect("stm_record.db")
    cursor = conn.cursor()
    # 创建订单表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_info (
            UID INTEGER PRIMARY KEY AUTOINCREMENT,  -- 编号
            OSN TEXT NOT NULL,  
            TS TEXT,
            SR TEXT,
            TEST_ID TEXT
        )
    """)    
    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)

        # --------------------
        # 主线程操作区
        l = inst_redis.xreadgroup("stream_reading_confirm","ReadingConfirm","ReadingConfirm-DB01")

        if len(l)>0 :                       # 收到消息
            # print(l)                        # Only for debug
            inst_logger.info("收到序列 %s 中的消息累计 %d 行" %(l[0][0],len(l[0][1])))
            for i,dictdata in l[0][1]:             # 遍历收到的所有消息
                try:
                    cursor.execute('INSERT INTO order_info (OSN,TS,SR,TEST_ID) VALUES (?,?,?,?)',
                           (dictdata['barcode'],dictdata['ts'],dictdata['scan_result'],dictdata['uid']))
                    # Only for debug
                    inst_logger.debug("SQLite DB 写入成功,条码 %s,时间戳 %s,扫描结果 %s, 扫描ID %s" %(dictdata['barcode'],dictdata['ts'],dictdata['scan_result'],dictdata['uid']))        
                    # Only for debug
                except sqlite3.IntegrityError:
                    inst_logger.debug("SQLite DB 写入失败！！,条码 %s,时间戳 %s,扫描结果 %s, 扫描ID %s" %(dictdata['barcode'],dictdata['ts'],dictdata['scan_result'],dictdata['uid']))  
                
                finally:
                    conn.commit()
                
        # --------------------
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        
        # 线程运行时间与健康程度判断
        inst_redis.ct_refresh(__prc_name__)
        
        # cycletime 计算 与 healthy判断
        # ToDo 
        
                
        # 线程是否继续运行的条件判断
        
        #如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:  
            # --------------------
            # 以下为定制区域，用于中止线程内创建的线程或调用的函数            inst_redis.xdelgroup("stream_test", "HIKC_data")
            for i, e in enumerate(inst_redis.lstException):
                inst_logger.error(
                    "线程 %s 超时退出时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                    % (__prc_name__,e['module'], e['timestamp'], e['msg']))
            inst_redis.lstException.clear()
            inst_logger.info("线程 %s 删除stream组成功" %("HIKC_data",))
            # 以上为定制区域，用于中止线程内创建的线程或调用的函数           
            # --------------------

            int_exit_code = 1           
            break
        
        #如command区收到退出命令，根据线程类型决定是否立即退出
        prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:command")
        if prc_run_lock == "exit":
            # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
            # 如有则暂缓退出，如没有立即退出
            inst_redis.xdelgroup("stream_test", "HIKC_data")
            for i, e in enumerate(inst_redis.lstException):
                inst_logger.error(
                    "线程 %s 超时退出时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                    % (__prc_name__,e['module'], e['timestamp'], e['msg']))
            inst_redis.lstException.clear()
            inst_logger.info("线程 %s 删除stream组成功" %("HIKC_data",))

            int_exit_code = 2          
            break
    conn.close()
    inst_logger.info("线程 %s 已退出，返回代码为 %d" %(__prc_name__,int_exit_code))




