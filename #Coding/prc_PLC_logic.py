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
    def sendPLC_barcode(CV02_barcode, current_time):
        LID = 'SRF_' + str(int(time.time()))
        barcode_bytes = bytearray(LID, 'utf-8')
        inst_redis.xadd("stream_plc_confirm",
                        {"db": "12",
                         "start_size": f"{__CV02_barcode__}", "data": f"{barcode_bytes}",
                         "req_ts": f"{current_time}"})

    __prc_name__ = "PLC_logic"  ### 需手动配置成线程名称

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
    __DB12__ = __ini_prc_config__.plc_info.DB12
    __CV02_barcode__ = __ini_prc_config__.plc_info.CV02_barcode
    __CV02_wcs__ = __ini_prc_config__.plc_info.CV02_wcs
    __CV02_taskid__ = __ini_prc_config__.plc_info.CV02_taskid
    __CV05_taskid__ = __ini_prc_config__.plc_info.CV05_taskid
    __CV11_taskid__ = __ini_prc_config__.plc_info.CV11_taskid
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


    # 以上为定制初始化区域
    # --------------------    

    # 主线程变量初始化：启动变量，退出返回值
    b_thread_running = True
    int_exit_code = 0

    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock", __prc_id__, __prc_expiretime)
        current_time = datetime.datetime.now().isoformat()  # 获取当前时间并转换为 ISO 格式
        # --------------------
        # 以下为主线程操作区
        # 获取redis中数据，进行逻辑处理
        CV02_SensorStatus = inst_redis.getkey("plc_conv:CV02:SensorStatus")
        CV02_barcode = inst_redis.getkey("plc_conv:CV02:Barcode")
        # 如果cv2状态为2且barcode为0 执行逻辑 先空着
        if CV02_SensorStatus == '2' and CV02_barcode == 0:
            sendPLC_barcode(__CV02_barcode__, current_time)
            LID = 'SRF_' + str(int(time.time()))
            barcode_bytes = bytearray(LID, 'utf-8')
            inst_redis.xadd("stream_plc_confirm",
                            {"db": "12", "start_size": f"{__CV02_barcode__}", "data": f"{barcode_bytes}", "req_ts": f"{current_time}"})
        # cv2有条码 并且状态为1   下发确认放行  下发目的地4

        # 如果cv4上有条码  给通道机下发条码

        # 通道机返回的条码经过判断，去7 或者12  记录在redis中

        # 如果cv5上有条码，且状态为2  查目的地 然后下发目的地

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
