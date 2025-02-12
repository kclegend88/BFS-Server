# prc_template  v 0.3.0
import json
import threading
import time
import datetime

import snap7

from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis


def start_process(config_file):
    def PLC_connect(inst_logger, __inst_plc__, __plc_ip__):
        while True:
            try:
                __inst_plc__.connect(__plc_ip__, 0, 1)  # 连接到PLC
                if __inst_plc__.get_connected():
                    inst_logger.error("线程 PLC PLC连接成功。")
                    break
                else:
                    inst_logger.error("线程 PLC PLC连接失败，三秒后重连")
                time.sleep(3)
            except Exception as e:
                inst_logger.error("线程 PLC PLC连接失败，三秒后重连")
                time.sleep(3)


    __prc_name__ = "PLC_write"  ### 需手动配置成线程名称

    ini_config = clsConfig(config_file)  # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)  # 实际上与主线程使用的是同一实例
    inst_redis = clsRedis(ini_config)  # 实际上与主线程使用的是同一实例

    inst_logger.info("线程 %s 正在启动" % (__prc_name__,))

    # 本地ini文件读取
    str_ini_file_name = "prc_%s.ini" % (__prc_name__,)
    __ini_prc_config__ = clsConfigEx(str_ini_file_name)
    __prc_cycletime = __ini_prc_config__.CycleTime.prc_cycletime
    __prc_expiretime = __ini_prc_config__.CycleTime.prc_expiretime
    __prc_healthytime = __ini_prc_config__.CycleTime.prc_healthytime

    # --------------------    
    # 定制化配置参数读取区
    __plc_ip__ = __ini_prc_config__.Sever.PLC_server_ip
    __plc_db_size = __ini_prc_config__.plc_info.DB3_size
    # 定制化配置参数读取区
    # --------------------

    # 系统将初始化信息写入Redis
    __prc_id__ = inst_redis.init_prc(__prc_name__, __prc_expiretime)
    if not __prc_id__:  # 取得异常消息队列中的信息
        for i, e in enumerate(inst_redis.lstException):
            inst_logger.error(
                "线程 %s 注册 Redis 服务器失败，调用模块 %s，调用时间 %s，异常信息 %s "
                % (__prc_name__, e['module'], e['timestamp'], e['msg']))
        inst_redis.lstException.clear()
        return  # Redis 注册失败失败

    # --------------------    
    # 以下为定制初始化区域
    __inst_plc__ = snap7.client.Client()
    # 连接PLC
    inst_logger.info(f"线程{__prc_name__}尝试连接 PLC")
    PLC_connect(inst_logger, __inst_plc__, __plc_ip__)
    stream_name_plc = "stream_plc_confirm"
    # 检查并创建消费组
    group_name = __prc_name__
    try:
        inst_redis.xcreategroup(stream_name_plc, __prc_name__)
        inst_logger.info("线程 %s 注册stream组成功" % (__prc_name__,))
    except Exception as e:
        inst_logger.info("线程 %s 注册stream组失败，该组已存在" % (__prc_name__,))
    # 以上为定制初始化区域
    # --------------------    

    # 主线程变量初始化：启动变量，退出返回值
    b_thread_running = True
    int_exit_code = 0

    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock", __prc_id__, __prc_expiretime)
        # --------------------
        # 以下为主线程操作区
        # 获取redis中readingconfirm数据，如果获取到数据，改变格式json格式，则提交到dss服务器上
        stream_plc_confirm = inst_redis.xreadgroup(stream_name_plc, group_name, "consumer1")
        if stream_plc_confirm:
            inst_logger.info(
                "收到序列 %s 中的消息累计 %d 行" % (stream_plc_confirm[0][0], len(stream_plc_confirm[0][1])))
            for i, dictdata in stream_plc_confirm[0][1]:
                db = dictdata['db']
                start_size = dictdata['start_size']
                plc_data = dictdata['plc_data']
                req_ts = dictdata['req_ts']
                inst_logger.info(f"stream_plc_confirm获取到数据：db: {db},start_size: {start_size},plc_data: {plc_data},"
                                 f"req_ts: {req_ts}")
                __inst_plc__.db_write(db, start_size, plc_data)
        # 以上为主线程操作区
        # --------------------
        time.sleep(__prc_cycletime / 1000.0)  # 所有时间均以ms形式存储

        # 线程运行时间与健康程度判断
        inst_redis.ct_refresh(__prc_name__)
        # ToDo

        # 线程是否继续运行的条件判断

        # 如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock = inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:
            # --------------------
            # 以下为定制区域，用于中止线程内创建的线程或调用的函数

            # 以上为定制区域，用于中止线程内创建的线程或调用的函数           
            # --------------------
            int_exit_code = 1
            break

        # 如command区收到退出命令，根据线程类型决定是否立即退出
        prc_run_lock = inst_redis.getkey(f"pro_mon:{__prc_name__}:command")
        if prc_run_lock == "exit":
            # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
            # 如有则暂缓退出，如没有立即退出
            int_exit_code = 2
            break

    inst_logger.info("线程 %s 已退出，返回代码为 %d" % (__prc_name__, int_exit_code))
