# prc_template  v 0.3.0
import sys
sys.path.append("..")
import time
import datetime
import pygame
from fBarcode import barcode_formatcheck
from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis
from pygame import mixer

def start_process(config_file,__cli_id__):
    __prc_cli_type__=f"cli_manualscan"
    __prc_name__=f"cli%02d_manualscan"%(__cli_id__,)
    
    ini_config = clsConfig(config_file)   # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)   # 实际上与主线程使用的是同一实例
    inst_redis = clsRedis(ini_config)     # 实际上与主线程使用的是同一实例

    inst_logger.info("线程 %s 正在启动"%(__prc_name__,))

    # 本地ini文件读取
    # str_ini_file_name = "prc_%s.ini" % (__prc_name__,)
    str_ini_file_name = "prc_%s.ini" % (__prc_cli_type__,)
    __ini_prc_config__ = clsConfigEx(str_ini_file_name)
    __prc_cycletime = __ini_prc_config__.CycleTime.prc_cycletime
    __prc_expiretime = __ini_prc_config__.CycleTime.prc_expiretime
    __prc_healthytime = __ini_prc_config__.CycleTime.prc_healthytime

    # --------------------
    # 定制化配置参数读取区
    # 取得ini文件中的全部声音资源列表
    # ToDo 自动遍历ini文件中，Sound字段下的配置文件
    dict_sound = {}
    dict_sound['ms_barcode_reject']= __ini_prc_config__.Sound.ms_barcode_reject
    dict_sound['ms_barcode_exist']= __ini_prc_config__.Sound.ms_barcode_exist
    dict_sound['ms_barcode_rescan_accpet']= __ini_prc_config__.Sound.ms_barcode_rescan_accpet

    # 取得ini文件中的全部条码正则表达式列表
    # ToDo 自动遍历ini文件中，barcode字段下的所有正则表达式
    lst_re_exp = []
    lst_re_exp.append(__ini_prc_config__.Barcode.re_exp_01)
    lst_re_exp.append(__ini_prc_config__.Barcode.re_exp_02)
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
        return       # Redis 注册失败

    # --------------------
    # 以下为定制初始化区域
    # 初始化pygame.mixer
    pygame.mixer.init()
    lst_reading_gr =[]
    # lst_reading_nr =[]
    lst_reading_mr =[]

    # 以上为定制初始化区域
    # --------------------

    b_thread_running = True
    int_exit_code = 0
    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock", __prc_id__, __prc_expiretime)
        # --------------------
        # 主线程操作区
        # strManualScanBarcode = input("please enter manual scan barcode...")
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        for i, e in enumerate(inst_redis.lstException):
            inst_logger.error(
                "线程 %s 运行时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                % (__prc_name__, e['module'], e['timestamp'], e['msg']))
        inst_redis.lstException.clear()
        # 取得QT窗口拦截的键盘输入，即扫描枪扫描数据
        strManualScanBarcode = inst_redis.getkey(f"manualscan:cli{__cli_id__:02}_qt:input")
        #strManualScanBarcode = inst_redis.getkey(f"manualscan:cli00_qt:input")
        lst_reading_nr = list(inst_redis.getset("set_reading_nr"))  # 更新set_reading_nr
        set_reading_mr = inst_redis.getset("set_reading_mr")  # 更新set_reading_mr
        if len(lst_reading_nr) + len(set_reading_mr) == 0:  # 正常状态，不需要补码
            continue
        if strManualScanBarcode:        # 如果接收缓冲区不为空
            inst_logger.info(f"收到QT传来的补码条码：$${strManualScanBarcode}$$")
            inst_redis.setkey(f"manualscan:cli{__cli_id__:02}_qt:input", "")    # 清空缓冲区

            # 更新set_reading_gr
            lst_reading_gr = inst_redis.getset("set_reading_gr")
            # 更新set_reading_nr
            # lst_reading_nr = inst_redis.getset("set_reading_nr")
            # 更新set_reading_mr
            lst_reading_mr = inst_redis.getset("set_reading_mr")         

            # 如果条码开头为"##" 说明该条码为手动输入框输入条码或特殊条码
            if strManualScanBarcode.startswith("*"):       # 条码破损或其他原因导致的手动输入条码
                str_special = strManualScanBarcode[1:]      # 取得条码本体
                inst_logger.info(f"识别到该条码为特殊条码,条码信息为：$${str_special}$$")

                if str_special == "clean*":        # 进入清场模式
                    inst_logger.info(f"识别到清场命令，将系统状态更改为clean")
                    inst_redis.setkey("sys:status","clean")
                    continue

                if str_special in lst_reading_gr:           # 如果手动输入的条码属于GR清单,不予接受
                    inst_logger.info("特殊条码已存在于扫描清单中,Barcode is already exist!!")
                    mixer.music.load(dict_sound['ms_barcode_exist'])
                    mixer.music.play()
                    continue

                if str_special in lst_reading_mr:           # 如果手动输入的条码属于MR清单,填加至序列等待处理
                    inst_logger.info("Get SPECIAL    MRead Barcode !!")
                    inst_redis.xadd( "stream_manualscan", {'cli_id':__cli_id__,'scan_id':__prc_id__,'barcode':str_special,'type':'MR'})
                    mixer.music.load(dict_sound['ms_barcode_rescan_accept'])
                    mixer.music.play()
                    continue

                else: 
                    bBarcodeValid = False
                    for i, re_exp in enumerate(lst_re_exp):         # 遍历所有正则表达式，任何一个通过就说明条码被接受
                        if barcode_formatcheck(str_special,re_exp): # 如果手动输入的条码通过正则校验,填加至序列等待处理
                            inst_logger.info("Get SPECIAL    NoRead Barcode !!")
                            inst_redis.xadd( "stream_manualscan", {'cli_id':__cli_id__,'scan_id':__prc_id__,'barcode':str_special,'type':'NR'})
                            bBarcodeValid = True
                            mixer.music.load(dict_sound['ms_barcode_rescan_accpet'])
                            mixer.music.play()                
                            continue
                    if not bBarcodeValid:                           # 所有正则表达式均未通过
                        inst_logger.info("特殊条码不符合条码规则.SPECIAL Barcode is not valid!!")
                        mixer.music.load(dict_sound['ms_barcode_reject'])
                        mixer.music.play()
                        continue

            if strManualScanBarcode in lst_reading_gr:
                inst_logger.info("条码已存在于扫描清单中,Barcode is already exist!!")
                mixer.music.load(dict_sound['ms_barcode_exist'])
                mixer.music.play()
                continue
            
            if strManualScanBarcode in lst_reading_mr:      
                inst_logger.info("Get MRead Barcode !!")
                inst_redis.xadd( "stream_manualscan", {'cli_id':__cli_id__,'scan_id':__prc_id__,'barcode':strManualScanBarcode,'type':'MR'})      # 插入 Manual Scan stream/MR
                mixer.music.load(dict_sound['ms_barcode_rescan_accpet'])
                mixer.music.play()
                continue
            
            # 条码格式校验
            bBarcodeValid = False
            for i, re_exp in enumerate(lst_re_exp):                 # 遍历所有正则表达式，任何一个通过就说明条码被接受
                if barcode_formatcheck(strManualScanBarcode,re_exp):    # 如果条码通过正则校验,填加至序列等待处理
                    inst_logger.info("Get SPECIAL    NoRead Barcode !!")
                    inst_redis.xadd( "stream_manualscan", {'cli_id':__cli_id__,'scan_id':__prc_id__,'barcode':strManualScanBarcode,'type':'NR'})      # 插入 Manual Scan stream/NR
                    bBarcodeValid = True
                    mixer.music.load(dict_sound['ms_barcode_rescan_accpet'])
                    mixer.music.play()                
                    break
            if not bBarcodeValid:
                inst_logger.info("条码不符合条码规则.SPECIAL Barcode is not valid!!")
                mixer.music.load(dict_sound['ms_barcode_reject'])
                mixer.music.play()
            # --------------------
            # time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        
        # 线程运行时间与健康程度判断
        inst_redis.ct_refresh(__prc_name__)
        # 线程是否继续运行的条件判断
        
        #如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:  
            int_exit_code = 1           
            break
        
        #如command区收到退出命令，根据线程类型决定是否立即退出
        prc_run_lock=inst_redis.getkey(f"sys:cli{__cli_id__:02}:command")
        if prc_run_lock == "exit":
            inst_logger.info("线程 %s 已收到退出信号" %(__prc_name__,))
            # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
            # 如有则暂缓退出，如没有立即退出

            int_exit_code = 2           
            break
    inst_redis.clearkey(f"pro_mon:{__prc_name__}:run_lock")
    inst_logger.info("线程 %s 已退出，返回代码为 %d" %(__prc_name__,int_exit_code))
