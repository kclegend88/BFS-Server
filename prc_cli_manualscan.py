# prc_template  v 0.2.0
import time
import datetime
from fBarcode import barcode_formatcheck
from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis

def start_process(config_file):
    __prc_name__="cli_manualscan"
    
    ini_config = clsConfig(config_file)   # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)  
    inst_redis = clsRedis(ini_config)
    inst_logger.info("线程 %s 正在启动" %(__prc_name__,))
    
    # cli 使用 Redis Ex,各自使用独立实例,每次初始化后都需要重连
    inst_redis.connect(ini_config)
    inst_logger.info("Redis 连接成功")
    
    # 本地ini文件存储的本线程专有配置参数
    # 定义线程循环时间、过期时间、健康时间等
    str_ini_file_name = "prc_%s.ini" %(__prc_name__,)
    __ini_prc_config__=clsConfigEx(str_ini_file_name)
    
    __prc_cycletime=__ini_prc_config__.CycleTime.prc_cycletime
    __prc_expiretime=__ini_prc_config__.CycleTime.prc_expiretime
    __prc_healthytime=__ini_prc_config__.CycleTime.prc_healthytime
    
    # 取得ini文件中的全部条码正则表达式列表
    # ToDo 自动遍历ini文件中，barcode字段下的所有正则表达式
    lst_re_exp = []
    lst_re_exp.append(__ini_prc_config__.Barcode.re_exp_01)
    lst_re_exp.append(__ini_prc_config__.Barcode.re_exp_02)
    
    # 向Redis注册基本信息，允许同名客户端，根据已注册的同名客户端自动取得两位数的尾号，不允许超过90个同名客户端在线
    prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
    if prc_run_lock:
        index = 0
        while prc_run_lock:
            index = index + 1
            if index > 90:
                inst_logger.error("线程 %s 启动时发现了过多客户端同时在运行，退出！")
                sys.exit(1)
            prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}-%02d:run_lock"%(index,))
            
    __cli_id__ = index
    # 增加Redis中总线程计数器，并将增加后的计数器值作为当前线程的id
    __prc_id__ = inst_redis.incrkey(f"pro_mon:prc_counter")
    
    inst_logger.info("线程 %s 取得 prc_id = %d, cli_id = %d"%(__prc_name__,__prc_id__,__cli_id__)) 
    # inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
    inst_redis.setkey(f"pro_mon:{__prc_name__}:run_lock",__prc_id__)             ## manucal scan函数不允许超时 ##      
    #inst_logger.info("线程 %s 已设置线程锁，过期时间 = %d ms"%(__prc_name__,__prc_expiretime)) 
    inst_logger.info("线程 %s 已设置线程锁，过期时间 = %d ms"%(__prc_name__,-1))      ## manucal scan函数不允许超时 ##

    # 增加当前线程的重启次数,如为1说明是首次启动
    # __prc_restart__ = inst_redis.incrkey(f"pro_mon:{__prc_name__}:restart")           ## manucal scan函数不记录重启 ##
    # inst_logger.info("线程 %s 启动次数 restart = %d"%(__prc_name__,__prc_restart__))    ## manucal scan函数不记录重启 ##
        
    # 记录线程启动时间
    __prc_start_ts__ = datetime.datetime.now()
    inst_redis.setkey(f"pro_mon:{__prc_name__}:start_ts",__prc_start_ts__.isoformat())
    inst_logger.info("线程 %s 启动时间 start_ts= %s"%(__prc_name__,__prc_start_ts__.isoformat()))
        
    # 记录线程上次刷新时间，用于持续计算线程的cycletime
    prc_luts=__prc_start_ts__
    inst_redis.setkey(f"pro_mon:{__prc_name__}:lu_ts",prc_luts.isoformat())
        
    # 将当前线程加入Redis 线程集合中
    inst_redis.sadd("set_cli_process","name=%s/prc_id=%d/cli_id=%d"%(__prc_name__,__prc_id__,__cli_id__)) ## 区别于main 函数, cli加入set_cli_process中
    inst_logger.info("线程 %s 已添加至线程集合中" %(__prc_name__,))
   
    b_thread_running = True
    int_exit_code = 0
    while b_thread_running:
        # 刷新当前线程的运行锁
        # inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
        # inst_redis.setkey(f"pro_mon:{__prc_name__}:run_lock",__prc_id__)             ## manucal scan函数不允许超时     
        
        # --------------------
        # 主线程操作区
        strManualScanBarcode = input("please enter manual scan barcode...")
        
        # 更新set_reading_gr
        
        # 更新set_reading_mr
        
        # 更新set_reading_nr
                
        # 条码格式校验
        for i, re_exp in enumerate(lst_re_exp):
            if barcode_formatcheck(strManualScanBarcode,re_exp):
                inst_redis.xadd( "stream_manualscan", {'scanid':__prc_id__,'barcode':strManualScanBarcode})      # 插入 Manual Scan stream
                print("Barcode valid,insert into system")
                break
        print("Barcode is not valid!!")
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
    inst_redis.clearkey(f"pro_mon:{__prc_name__}-%02d:run_lock"%(__cli_id__,))
    inst_logger.info("线程 %s 已退出，返回代码为 %d" %(__prc_name__,int_exit_code))




