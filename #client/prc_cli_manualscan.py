# prc_template  v 0.3.0
import sys
sys.path.append("..")
import time
import datetime
import pygame
from fBarcode import barcode_existingcheck
from fVerificationDialog import VerificationDialog
from PyQt5.QtWidgets import QDialog
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
    dict_sound['ms_barcode_rescan_accept']= __ini_prc_config__.Sound.ms_barcode_rescan_accept
    dict_sound['check_ng']=__ini_prc_config__.Sound.check_ng

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
    int_set_check_ng_count_his = 0
    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock", __prc_id__, __prc_expiretime)
        # --------------------
        # 主线程操作区
        # strManualScanBarcode = input("please enter manual scan barcode...")
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
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        for i, e in enumerate(inst_redis.lstException):
            inst_logger.error(
                "线程 %s 运行时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                % (__prc_name__, e['module'], e['timestamp'], e['msg']))
        inst_redis.lstException.clear()
        # 取得QT窗口拦截的键盘输入，即扫描枪扫描数据
        strManualScanBarcode = inst_redis.getkey(f"manualscan:cli{__cli_id__:02}_qt:input")
        lst_reading_nr = list(inst_redis.getset("set_reading_nr"))  # 更新set_reading_nr
        set_reading_mr = inst_redis.getset("set_reading_mr")  # 更新set_reading_mr
        sys_status = inst_redis.getkey("sys:status")    #更新系统状态
        set_check_ng = inst_redis.getset("set_check_ng")    # 更新set_check_ng

        if strManualScanBarcode == "__clean__":  # 特定的清场命令
            inst_logger.info("收到__clean__命令，向服务器发送离开清场模式的指令")
            inst_redis.setkey(f"manualscan:cli{__cli_id__:02}_qt:input", "")  # 清空缓冲区
            inst_redis.xadd("stream_manualscan",
                            {'cli_id': __cli_id__, 'scan_id': __prc_id__, 'barcode': strManualScanBarcode,
                             'type': '**'})  # 插入 Manual Scan stream/MR
            mixer.music.load(dict_sound['ms_barcode_rescan_accept'])
            mixer.music.play()
            continue
        if len(lst_reading_nr) + len(set_reading_mr) + len(set_check_ng)== 0:  # 正常状态，不需要补码
        # if len(lst_reading_nr) + len(set_reading_mr) == 0:  # 正常状态，不需要补码
            continue

        # 查询set_check_ng中的条码数量，如果与上次不同，生成一条日志，播放声音
        # if int_set_check_ng_count_his < len(set_check_ng):
        #     inst_logger.debug("系统正常运行时，收到NG代码, NG货物数量由 %s 变为 %s " % (int_set_check_ng_count_his,len(set_check_ng)))
        #     mixer.music.load(dict_sound['check_ng'])
        #     mixer.music.play()
        # int_set_check_ng_count_his = len(set_check_ng)

        # 查询set_check_ng中的条码数量，如果不为空，且系统状态为normal，则转入alert
        # if len(set_check_ng) > 0 and sys_status == "normal":
            # Only for debug
        #    plc_conv_fullspeed = inst_redis.getkey("plc_conv:fullspeed")
        #    if plc_conv_fullspeed == "yes":
        #        inst_logger.info("发送减速信号autoslowdown，条码读取异常，NG")
        #        inst_redis.setkey(f"plc_conv:command", "autoslowdown")  # slow down conv
        #        inst_redis.setkey("sys:status", "alert")

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


            # 如果条码开头为"##" 说明该条码为手动输入框输入条码或特殊条码
            if strManualScanBarcode.startswith("*"):       # 条码破损或其他原因导致的手动输入条码
                str_special = strManualScanBarcode[1:]      # 取得条码本体
                inst_logger.info(f"识别到该条码为特殊条码,条码信息为：$${str_special}$$")
                # if str_special == "clean*":        # 进入清场模式
                #    inst_logger.info(f"识别到清场命令，将系统状态更改为clean")
                #    inst_redis.setkey("sys:status","clean")
                #    continue

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
                            mixer.music.load(dict_sound['ms_barcode_rescan_accept'])
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
                mixer.music.load(dict_sound['ms_barcode_rescan_accept'])
                mixer.music.play()
                continue

            if strManualScanBarcode in set_check_ng:
                inst_logger.info("Catch NG Barcode !!")
                mixer.music.load(dict_sound['ms_barcode_rescan_accept'])
                mixer.music.play()
                # 创建并使用对话框
                # dialog = VerificationDialog()
                # result = dialog.exec_()
                #
                # if result == QDialog.Accepted:
                #     # 成功捕获NG包裹，且扫描了正确的框号
                #     inst_redis.sadd("set_check_ng_catch", strManualScanBarcode)  # set_check_ng_catch
                #     inst_logger.info(
                #         "NG包裹捕获成功,线程 %s 将NG包裹 %s 加入set_check_ng_catch中" % (__prc_name__, strManualScanBarcode))
                #     continue
                # else:
                #     inst_logger.info(
                #         "NG包裹扫描成功，捕获失败,线程 %s 未能将NG包裹 %s 加入set_check_ng_catch中" % (__prc_name__, strManualScanBarcode))
                #     continue

            # 条码格式校验
            bBarcodeValid = False
            for i, re_exp in enumerate(lst_re_exp):                 # 遍历所有正则表达式，任何一个通过就说明条码被接受
                if barcode_formatcheck(strManualScanBarcode,re_exp):    # 如果条码通过正则校验,填加至序列等待处理
                    inst_logger.info("收到补码条码 %s，校验通过，开始检查单据状态!!"%(strManualScanBarcode,))
                    # 条码正确读取，开始进行条码规则判断
                    # 如果包裹为OK，result设为 NG_xx，
                    # 如果包裹为OK，result设为 GR
                    # 此处只做两个判断，a: 是否在主单中，不是则为OP; b: 是否为通缉，是则为RJ，不是则为OK
                    # 对每一个GR和MR的进行检查
                    set_hawb = inst_redis.getset("set_hawb")
                    set_hawb_rj = inst_redis.getset("set_hawb_rj")
                    bc_result = 'NR'
                    if barcode_existingcheck(strManualScanBarcode, set_hawb_rj):  # 通缉件
                        bc_result = 'NG_NR_RJ'
                    if not barcode_existingcheck(strManualScanBarcode, set_hawb):  # 溢装件
                        bc_result = 'NG_NR_OP'
                    inst_redis.xadd( "stream_manualscan", {'cli_id':__cli_id__,'scan_id':__prc_id__,'barcode':strManualScanBarcode,'type':bc_result})      # 插入 Manual Scan stream/NR
                    bBarcodeValid = True
                    if bc_result == 'NR':
                        mixer.music.load(dict_sound['ms_barcode_rescan_accept'])
                    else:
                        mixer.music.load(dict_sound['check_ng'])
                    mixer.music.play()
                    break
            if not bBarcodeValid:
                inst_logger.info("条码不符合条码规则.SPECIAL Barcode is not valid!!")
                mixer.music.load(dict_sound['ms_barcode_reject'])
                mixer.music.play()
            # --------------------
            # time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
           
        
    inst_redis.clearkey(f"pro_mon:{__prc_name__}:run_lock")
    inst_logger.info("线程 %s 已退出，返回代码为 %d" %(__prc_name__,int_exit_code))
