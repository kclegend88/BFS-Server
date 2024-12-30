# prc_template  v 0.2.0
import time
import datetime
from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis
import ast

def start_process(config_file):
    __prc_name__="stmManualScan"
    
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
    
    # 向Redis注册基本信息
    prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
    if prc_run_lock is None:    
        # Redis中不存在该线程的运行锁，说明没有同名线程正在运行，无线程冲突，可以直接启动
        # 增加Redis中总线程计数器，并将增加后的计数器值作为当前线程的id
        __prc_id__ = inst_redis.incrkey(f"pro_mon:prc_counter")
        inst_logger.info("线程 %s 取得 id = %d"%(__prc_name__,__prc_id__)) 
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
        inst_logger.info("线程 %s 已设置线程锁，过期时间 = %d ms"%(__prc_name__,__prc_expiretime)) 

        # 增加当前线程的重启次数,如为1说明是首次启动
        __prc_restart__ = inst_redis.incrkey(f"pro_mon:{__prc_name__}:restart")
        inst_logger.info("线程 %s 启动次数 restart = %d"%(__prc_name__,__prc_restart__)) 
        
        # 记录线程启动时间
        __prc_start_ts__ = datetime.datetime.now()
        inst_redis.setkey(f"pro_mon:{__prc_name__}:start_ts",__prc_start_ts__.isoformat())
        inst_logger.info("线程 %s 启动时间 start_ts= %s"%(__prc_name__,__prc_start_ts__.isoformat()))
        
        # 记录线程上次刷新时间，用于持续计算线程的cycletime
        prc_luts=__prc_start_ts__
        inst_redis.setkey(f"pro_mon:{__prc_name__}:lu_ts",prc_luts.isoformat())
        
        # 将当前线程加入Redis 线程集合中
        inst_redis.sadd("set_process","name=%s/id=%d"%(__prc_name__,__prc_id__))
        inst_logger.info("线程 %s 已添加至线程集合中" %(__prc_name__,))
                
    else:
        # Redis中存在该线程的运行锁，说明已经有同名线程正在运行
        # 记录线程冲突错误并退出
        # ToDo 将此类重要错误 使用stm_sys_log进行永久化记录
        inst_logger.error("线程 %s 启动时发现了运行冲突,同名线程已存在,id= %d"%(__prc_name__,prc_run_lock))
        exit()
    
    if not inst_redis.xcreategroup("stream_manualscan", "manualscan"):
        inst_logger.info("线程 %s 注册stream组失败，该组已存在" %("manualscan",))
    else:
        inst_logger.info("线程 %s 注册stream组成功" %("manualscan",))
    
    b_thread_running = True
    int_exit_code = 0
    
    dictdata={}
    lstdictdata=[]
    set_reading_mr={}
    lst_reading_nr=[]
    set_ms_mr={}
    lst_ms_nr=[]
    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)

        # --------------------
        # 主线程操作区
        l = inst_redis.xreadgroup("stream_manualscan","manualscan","manualscan-id01")

        if len(l)>0 :                       # 收到消息
            print(l)                        # Only for debug
            inst_logger.info("收到补码扫描序列 %s 中的消息累计 %d 行" %(l[0][0],len(l[0][1])))
            for i,v in l[0][1]:             # 遍历收到的所有消息
                dictdata = v                                            # redis decoding返回的是dict格式
                # inst_redis.sadd("set_ms", dictdata['barcode'])     # 将条码加入set_manualscan
                # 将条码发送给barcode check 模块
                # 如果返回的是ok，那么仅仅进行扫描补码，补码条件满足就恢复输送机运行
                if dictdata['barcode'] == 'MR':
                    inst_redis.sadd("set_ms_mr", dictdata['barcode'])     
                else:
                    inst_redis.sadd("set_ms_nr", dictdata['barcode'])     
                # 如果返回的是各类异常 BL/OP/NF/SF/RC,那么需要反馈barcode check 异常，要求客户端执行剔除操作
        

        lst_reading_nr = list(inst_redis.getset("set_reading_nr"))  # 更新set_reading_nr
        lst_ms_nr = list(inst_redis.getset("set_ms_nr"))            # 更新set_ms_nr       
        set_reading_mr = inst_redis.getset("set_reading_mr")  # 更新set_reading_mr
        set_ms_mr = inst_redis.getset("set_ms_mr")            # 更新set_ms_mr

        if len(lst_reading_nr) + len(set_reading_mr) == 0:
            continue
        # 开始逻辑判断
        # set_ms_nr 的数量，与set_reading_nr的数量一致
        if not len(lst_ms_nr)== len(lst_reading_nr):
            continue
        # set_ms_mr 的 set_reading_mr 完全一致
        if not set_ms_mr == set_reading_mr:
            continue
        # 所有read_ng的包裹都已经被捕捉
        # 将read_nr/mr中的所有包裹，从set_reading mr/nr中删除，移动到set_reading_gr中，parcel:status更改成为mr_ms或者nr_ms

        for i,parcel_uid in enumerate(lst_reading_nr):
            inst_redis.setkey(f"parcel:scan_result:{parcel_uid}","NR_MS")
            inst_redis.setkey(f"parcel:barcode:{parcel_uid}",lst_ms_nr[i])
            inst_logger.info("包裹补码成功,线程 %s 修改NR包裹状态 uid= %s, barcode =%s"%(__prc_name__,parcel_uid,lst_ms_nr[i]))
        inst_redis.clearset("set_ms_nr")
        inst_redis.clearset("set_reading_nr")
            
        for parcel_barcode in set_reading_mr:
            parcel_uid = inst_redis.getkey(f"parcel:ms_barcode:{parcel_barcode}")
            inst_redis.setkey(f"parcel:scan_result:{parcel_uid}","MR_MS")
            inst_redis.setkey(f"parcel:barcode:{parcel_uid}",parcel_barcode)
            inst_logger.info("包裹补码成功,线程 %s 修改MR包裹状态 uid= %s, barcode =%s"%(__prc_name__,parcel_uid,parcel_barcode))
        inst_redis.clearset("set_ms_mr")       
        inst_redis.clearset("set_reading_mr")

        # 恢复输送机速度
        plc_conv_status = inst_redis.getkey("plc_conv:status")
        plc_conv_fullspeed = inst_redis.getkey("plc_conv:fullspeed")
        if plc_conv_status == 'run':
            if plc_conv_fullspeed == 'countdown':
                inst_redis.setkey("plc_conv:fullspeed",'Yes')       # 如果在运转，则plc_conv_fullspeed 应为countdown 15秒，更改fullspeed=yes即可恢复
                inst_logger.info("包裹补码成功，线程 %s 尝试将输送机恢复至正常速度" %(__prc_name__,))
            else:
                inst_logger.error("线程 %s 在恢复输送机速度时发现状态异常" %(__prc_name__,))
                continue
        else:
            inst_redis.setkey("plc_conv:command",'start')       # 如果不在运转，则说明已停机，需重新启动
            inst_logger.info("包裹补码成功，线程 %s 尝试重新启动输送机" %(__prc_name__,))
        # --------------------
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        
        # 线程运行时间与健康程度判断
                
        current_ts=datetime.datetime.now()  
        td_last_ct = current_ts - prc_luts  # datetime对象相减得到timedelta对象
        int_last_ct_ms = int(td_last_ct.total_seconds()*1000) # 取得毫秒数（int格式)
        
        prc_luts=current_ts # 刷新luts
        inst_redis.setkey(f"pro_mon:{__prc_name__}:lu_ts",current_ts.isoformat()) # 更新redis中的luts
               
        inst_redis.lpush(f"lst_ct:%s"%(__prc_name__,),int_last_ct_ms) # 将最新的ct插入redis中的lst_ct
        int_len_lst= inst_redis.llen(f"lst_ct:%s"%(__prc_name__,))  # 取得列表中元素的个数
        if int_len_lst > 10:
            inst_redis.rpop(f"lst_ct:%s"%(__prc_name__,))    # 尾部数据弹出
        # cycletime 计算 与 healthy判断
        # ToDo 
        
                
        # 线程是否继续运行的条件判断
        
        #如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:  
            int_exit_code = 1           
            break
        
        #如command区收到退出命令，根据线程类型决定是否立即退出
        prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:command")
        if prc_run_lock == "exit":
            # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
            # 如有则暂缓退出，如没有立即退出
            int_exit_code = 2          
            break
    
    inst_logger.info("线程 %s 已退出，返回代码为 %d" %(__prc_name__,int_exit_code))




