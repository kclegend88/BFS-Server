# prc_template  v 0.3.0
import json
import threading
import time
import fBarcode
import datetime

from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis
from fHIKCamera import clsHIKCameraClient



def start_process(config_file):
    
    def prc_stmhikc_dataproc(lstdata):
        nonlocal inst_logger,__prc_name__
        for i,dictdata in lstdata:             # 遍历收到的所有消息
            inst_redis.setkey(f"parcel:sid:{dictdata['uid']}",i)   # uid对应的Stream id
            inst_redis.setkey(f"parcel:posx:{dictdata['uid']}",dictdata['pos_x'])   # uid对应的包裹沿传输方向的位置，单位为mm，定时增加
            inst_redis.setkey(f"parcel:posy:{dictdata['uid']}",dictdata['pos_y'])   # uid对应的包裹沿宽度方向的位置，单位为mm，左侧为零
            if dictdata['result']=='GR':                                            # 正常识读
                inst_redis.setkey(f"parcel:barcode:{dictdata['uid']}",dictdata['code']) # uid对应的包裹，正确识读出来的条码
                inst_redis.setkey(f"parcel:scan_result:{dictdata['uid']}",'GR')    # uid对应的包裹，扫描结果 GR
                inst_redis.setkey(f"parcel:check_result:{dictdata['uid']}", '##')  # uid对应的包裹，核查结果 ##
                # inst_redis.setkey(f"parcel:ms_barcode:{dictdata['code']}",dictdata['uid'])  # 参照多条码读取出来的条码，对应的uid ，check ng时需要
                inst_redis.sadd("set_reading_gr", dictdata['code'])                     # GR的包裹，将条码加入set_reading_gr
                # Only for debug
                inst_logger.debug("读取结果 %s, 条码 %s, " %(dictdata['result'],dictdata['code']))        
                # Only for debug
                # check barcode, if ng, slow down conv, add to set_reading_ng
                # add to barcode check stm,

                # prc_stmhikc_barcodecheck(dictdata['code'])
            elif dictdata['result']=='MR':                                          # 多条码
                inst_redis.setkey(f"parcel:scan_result:{dictdata['uid']}",'MR')         # uid对应的包裹，扫描结果 MR
                inst_redis.setkey(f"parcel:check_result:{dictdata['uid']}", '##')  # uid对应的包裹，核查结果 ##
                inst_redis.setkey(f"parcel:barcode:{dictdata['uid']}",dictdata['code']) # uid对应的包裹，多条码读取出来的条码
                inst_redis.setkey(f"parcel:ms_barcode:{dictdata['code']}",dictdata['uid'])  # 多条码读取出来的条码，对应的uid 
                inst_redis.sadd("set_reading_mr", dictdata['code'])                     # MR的包裹，将条码加入set_reading_mr

                # Only for debug
                inst_logger.debug("----读取异常！ %s, 条码 %s, " %(dictdata['result'],dictdata['code']))        
                # Only for debug
                plc_conv_fullspeed = inst_redis.getkey("plc_conv:fullspeed")
                if plc_conv_fullspeed=="yes":
                    inst_logger.info("发送减速信号autoslowdown，条码读取异常，MR")                      
                    inst_redis.setkey(f"plc_conv:command","autoslowdown")            # slow down conv
                    inst_redis.setkey("sys:status", "alert")

            elif dictdata['result']=='NR':      # 无条码    
                inst_redis.setkey(f"parcel:barcode:{dictdata['uid']}",'NoBarcode')  # uid对应的包裹，多条码读取出来的条码
                inst_redis.setkey(f"parcel:scan_result:{dictdata['uid']}",'NR')     # uid对应的包裹，扫描结果 NR
                inst_redis.setkey(f"parcel:check_result:{dictdata['uid']}", '##')  # uid对应的包裹，核查结果 ##
                inst_redis.sadd("set_reading_nr", dictdata['uid'])                  # NR的包裹，无条码，将uid加入set_reading_nr
                # Only for debug
                inst_logger.debug("----读取异常！ %s, 条码 xxxxxxx, " %(dictdata['result'],))        
                # Only for debug
                plc_conv_fullspeed = inst_redis.getkey("plc_conv:fullspeed")
                if plc_conv_fullspeed=="yes":
                    inst_logger.info("发送减速信号autoslowdown，条码读取异常，NR")                      
                    inst_redis.setkey(f"plc_conv:command","autoslowdown")            # slow down conv
                    inst_redis.setkey("sys:status", "alert")
            #inst_redis.ACK("stream_test",i)
            #inst_redis.ACK("stream_test",i)
            elif dictdata['result']=='MS_AS':      # 异常停止时增加的条码
                inst_redis.setkey(f"parcel:barcode:{dictdata['uid']}", dictdata['code'])  # uid对应的包裹，正确补的出来的条码 
                inst_redis.setkey(f"parcel:scan_result:{dictdata['uid']}", 'MS_AS')  # uid对应的包裹，扫描结果 GR
                inst_redis.setkey(f"parcel:check_result:{dictdata['uid']}", '##')  # uid对应的包裹，核查结果 ##
                inst_redis.sadd("set_reading_gr", dictdata['code'])  # GR的包裹，将条码加入set_reading_gr
                # Only for debug
                inst_logger.debug("异常停线时添加读取结果 %s, 条码 %s, " % (dictdata['result'], dictdata['code']))
            elif dictdata['result'][0:2]=='NG':
                inst_redis.setkey(f"parcel:barcode:{dictdata['uid']}",dictdata['code']) # uid对应的包裹，正确识读出来的条码
                inst_redis.setkey(f"parcel:scan_result:{dictdata['uid']}",dictdata['result'])    # uid对应的包裹，扫描结果 GR
                inst_redis.sadd("set_check_ng", dictdata['code'])                     # NG的包裹，set_check_ng
                # Only for debug
                inst_logger.debug("----条码被拒绝，核查结果 %s, 条码 %s, " %(dictdata['result'],dictdata['code']))
                # Only for debug

                # prc_stmhikc_barcodecheck(dictdata['code'])
                plc_conv_fullspeed = inst_redis.getkey("plc_conv:fullspeed")
                if plc_conv_fullspeed == "yes":
                    inst_logger.info("发送减速信号autoslowdown，条码读取异常，NR")
                    inst_redis.setkey(f"plc_conv:command", "autoslowdown")  # slow down conv
                    inst_redis.setkey("sys:status", "alert")
            elif dictdata['result']=='NG_OP':
                pass


    __prc_name__="stmHIKC_data"             
    
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
    REST = inst_redis.xcreategroup("stream_test", "HIKC_data")
    if REST :   # 返回值不为空，说明异常信息
        inst_logger.info("线程 %s 注册stream组失败，该组已存在， %s " %("HIKC_data", REST))
        for i, e in enumerate(inst_redis.lstException):
            inst_logger.error(
                "线程 %s 运行过程中发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                % (__prc_name__,e['module'], e['timestamp'], e['msg']))
        inst_redis.lstException.clear()
    else:
        inst_logger.info("线程 %s 注册stream组成功, %s " %("HIKC_data",REST))
    # 以上为定制初始化区域
    # --------------------    

    # 主线程变量初始化：启动变量，退出返回值
    b_thread_running = True
    int_exit_code = 0

    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
        # --------------------
        # 以下为主线程操作区
        l = inst_redis.xreadgroup("stream_test","HIKC_data","HIKC_data-id01")
        if len(l)>0 :                       # 收到消息
            prc_stmhikc_dataproc(l[0][1])
        
        for i, e in enumerate(inst_redis.lstException):
            inst_logger.error(
                "线程 %s 运行过程中发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                % (__prc_name__,e['module'], e['timestamp'], e['msg']))            
        inst_redis.lstException.clear()
        # 以上为主线程操作区       
        # --------------------
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        
        # 线程运行时间与健康程度判断
        inst_redis.ct_refresh(__prc_name__)
        # 线程是否继续运行的条件判断
        
        #如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:  
            # --------------------
            # 以下为定制区域，用于中止线程内创建的线程或调用的函数
            inst_redis.xdelgroup("stream_test", "HIKC_data")
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
                    "线程 %s 受控退出时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                    % (__prc_name__,e['module'], e['timestamp'], e['msg']))
            inst_redis.lstException.clear()
            inst_logger.info("线程 %s 删除stream组 %s 成功" % (__prc_name__, "HIKC_data"))
            int_exit_code = 2
            break
    
    inst_logger.info("线程 %s 已退出，返回代码为 %d" %(__prc_name__,int_exit_code))

