# prc_template  v 0.3.0
import json
import threading
import time
import datetime

from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis
from fHIKCamera import clsHIKCameraClient



def start_process(config_file):

    __prc_name__="BarcodeCheck"
    
    ini_config = clsConfig(config_file)     # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)     # 实际上与主线程使用的是同一实例
    inst_redis = clsRedis(ini_config)       # 实际上与主线程使用的是同一实例

    inst_logger.info("线程 %s 正在启动" %(__prc_name__,))

    # 本地ini文件读取
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
    # 以上为定制初始化区域
    # --------------------    

    # 主线程变量初始化：启动变量，退出返回值
    b_thread_running = True
    int_exit_code = 0

    while b_thread_running:
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        
        # 线程运行时间与健康程度判断
        # ToDo
        # 线程是否继续运行的条件判断
        # 如线程运行锁过期或被从外部删除，则退出线程
        inst_redis.ct_refresh(__prc_name__)
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储

        prc_run_lock = inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:
            # --------------------
            # 以下为定制区域，用于中止线程内创建的线程或调用的函数
            inst_redis.xdelgroup("stream_test", "HIKC_data")
            for i, e in enumerate(inst_redis.lstException):
                inst_logger.error(
                    "线程 %s 超时退出时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                    % (__prc_name__, e['module'], e['timestamp'], e['msg']))
            inst_redis.lstException.clear()
            inst_logger.info("线程 %s 删除stream组成功" % ("HIKC_data",))
            # 以上为定制区域，用于中止线程内创建的线程或调用的函数
            # --------------------
            int_exit_code = 1
            break

        # 如command区收到退出命令，根据线程类型决定是否立即退出
        prc_run_lock = inst_redis.getkey(f"pro_mon:{__prc_name__}:command")
        if prc_run_lock == "exit":
            # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
            # 如有则暂缓退出，如没有立即退出

            inst_logger.info("线程 %s 删除stream组 %s 成功" % (__prc_name__, "manualscan"))
            for i, e in enumerate(inst_redis.lstException):
                inst_logger.error(
                    "线程 %s 受控退出时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                    % (__prc_name__, e['module'], e['timestamp'], e['msg']))
            inst_redis.lstException.clear()
            inst_redis.xdelgroup("stream_manualscan", "manualscan")
            int_exit_code = 2
            break

        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
        # --------------------
        # 以下为主线程操作区

        # 遍历parcel表中所有数据，如果barcode不是NoBarcode，且check_result是## 说明是新增的读取结果，需要进行检查
        parcel_keys = inst_redis.keys('parcel:barcode:*')
        for key in parcel_keys:
            parts = key.split(':')      # 分割键名 parts[0]='parcel', parts[1]='barcode',parts[2] 为 uid
            uid = parts[2]
            if len(parts) == 3 and parts[0] == 'parcel' and parts[1] == 'barcode':      # key是完整的键名
                barcode = inst_redis.getkey(key)                                        # 获取条码
                check_result = inst_redis.getkey(f"parcel:check_result:{uid}")     # 获取条码检查结果
                if barcode == "NoBarcode":
                    continue
                if check_result != "##":
                    continue
                # 如果不是无读，且没有条码检查结果，开始检查
                set_hawb = inst_redis.getset("set_hawb")
                # if barcode not in set_hawb:         # 不在set_hawb中，溢装
                #    check_result = "OP"
                #    inst_redis.setkey(f"parcel:check_result:{uid}", check_result)
                #    inst_logger.info("条码 %s 核查结果为: %s"%( barcode, check_result))
                #    inst_redis.sadd("set_check_ng",barcode)
                #    continue

                str_hawb_status = inst_redis.getkey(f"hawb:status:{barcode}")
                if not str_hawb_status:     # 初始状态为空属于SF System Fault 系统错误
                    check_result = "SF"
                    inst_redis.setkey(f"parcel:check_result:{uid}", check_result)
                    inst_redis.setkey(f"hawb:status:{barcode}", '500') # 暂时写500 认为HPK扫描完成
                    inst_logger.info("条码 %s 初始状态为空值，核查结果为: %s"%( barcode, check_result))
                    # inst_redis.sadd("set_check_ng")
                    inst_redis.sadd("set_check_ok",barcode)     # 后续在此处加入ini文件判断
                    continue

                hawb_status = int (str_hawb_status)
                # Todo 加入int转换的捕捉异常语句
                if hawb_status == 300:  # 该mawb 首单上线
                    check_result = "HPK"
                    inst_redis.setkey(f"parcel:check_result:{uid}", check_result)
                    inst_redis.setkey(f"hawb:status:{barcode}", '500')  # 暂时写500 认为HPK扫描完成
                    inst_logger.info("条码 %s 初始状态为空值，核查结果为: %s" % (barcode, check_result))
                    # inst_redis.sadd("set_check_ng")
                    inst_redis.sadd("set_check_ok", barcode)  # 后续在此处加入ini文件判断
                    continue

                    # 后续需要在此加入sys:mode和sys:opmode的判断
                    # 如果mode为z且opmode为hpk，应判断status 大于等于500
                    # 如果mode为z且opmode为out，应判断status 大于700

                if hawb_status == 400:  # HPK件正常上机
                    # 后续需要在此加入sys:mode和sys:opmode的判断
                    # 如果mode为z且opmode为hpk，正常
                    # 如果mode为z且opmode为out，漏扫HPK，应报警后人工处理
                    check_result = "HPK"
                    inst_redis.setkey(f"parcel:check_result:{uid}", check_result)
                    inst_redis.setkey(f"hawb:status:{barcode}", '500')  # 暂时写500
                    inst_logger.info("条码 %s 初始状态正常，核查结果为: %s" % (barcode, check_result))
                    # inst_redis.sadd("set_check_ng")
                    inst_redis.sadd("set_check_ok", barcode)
                    continue

                if  500 <= hawb_status< 700:  # 重复扫描
                    check_result = "RC"
                    inst_redis.setkey(f"parcel:check_result:{uid}", check_result)
                    inst_redis.setkey(f"hawb:status:{barcode}", f"{hawb_status+1}")  # 记录重复次数
                    inst_logger.info("条码 %s 重复上机,结果为: %s"%( barcode, check_result))
                    # inst_redis.sadd("set_check_ng")
                    inst_redis.sadd("set_check_ok",barcode)     # 后续在此处加入ini文件判断，rc是否判ng
                    continue
                if 700 <= hawb_status < 800:  # OUT件扫描，SF
                    # 后续需要在此加入sys:mode和sys:opmode的判断
                    # 如果mode为z且opmode为hpk，已OUT件扫描HPK，报系统错误，应停线！！
                    # 如果mode为z且opmode为out，已OUT件重复扫描OUT，待定
                    check_result = "SF"
                    inst_redis.setkey(f"hawb:status:{barcode}", '799')  # 暂时写799 区分于 500
                    inst_logger.info("条码 %s 重复上机,结果为: %s"%( barcode, check_result))
                    inst_redis.sadd("set_check_ok",barcode)     # 后续在此处加入ini文件判断
                    continue

                if hawb_status == 800:                 # U
                    # 在数据下载时 该包裹应已自动加入set_hawb_rj中
                    check_result = "UB"
                    inst_redis.setkey(f"parcel:check_result:{uid}", check_result)
                    inst_redis.setkey(f"hawb:status:{barcode}", '899')  # 暂时写899 区分于 500
                    inst_logger.info("条码 %s 已被UB处理，核查结果为: %s"%( barcode, check_result))
                    # inst_redis.sadd("set_check_ng",barcode) # 应停机处理，但当前尚无报警措施；

                    continue
                if hawb_status == 900:                 # DNG
                    # 在数据下载时 该包裹应已自动加入set_hawb_rj中
                    check_result = "DN"
                    inst_redis.setkey(f"parcel:check_result:{uid}", check_result)
                    inst_redis.setkey(f"hawb:status:{barcode}", '999')  # 暂时写999 区分于 500
                    inst_logger.info("条码 %s 未许可！！核查结果为: %s"%( barcode, check_result))
                    # inst_redis.sadd("set_check_ng",barcode)
                    continue
                if hawb_status == 901:                 # Reject
                    check_result = "RJ"
                    inst_redis.setkey(f"parcel:check_result:{uid}", check_result)
                    inst_redis.setkey(f"hawb:status:{barcode}", '999')  # 暂时写999 区分于 500
                    inst_logger.info("条码 %s 通缉件，核查结果为: %s"%( barcode, check_result))
                    # inst_redis.sadd("set_check_ng",barcode)
                    continue

                # 属于本mawb订单,未发现已知异常
                check_result = "OK"
                inst_redis.setkey(f"parcel:check_result:{uid}",check_result)
                inst_redis.setkey(f"hawb:status:{barcode}", '499')  # 暂时写499 区分于 500
                inst_logger.info("条码 %s 核查结果为: %s"%( barcode, check_result))
                inst_redis.sadd("set_check_ok",barcode)
                continue

        # 以上为主线程操作区
        # --------------------


    inst_logger.info("线程 %s 已退出，返回代码为 %d" %(__prc_name__,int_exit_code))

