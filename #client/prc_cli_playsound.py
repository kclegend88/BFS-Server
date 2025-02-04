# prc_template  v 0.2.0
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
    __prc_cli_type__=f"cli_playsound"
    __prc_name__=f"cli%02d_playsound"%(__cli_id__,)
    
    ini_config = clsConfig(config_file)   # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)  
    inst_redis = clsRedis(ini_config)
    inst_logger.info("线程 %s 正在启动"%(__prc_name__,))
    
    # cli 使用 Redis Ex,各自使用独立实例,每次初始化后都需要重连
    inst_redis.connect(ini_config)
    inst_logger.info("线程 %s Redis 连接成功"%(__prc_name__,))
    
    # 本地ini文件存储的本线程专有配置参数
    # 定义线程循环时间、过期时间、健康时间等
    str_ini_file_name = "prc_%s.ini" %(__prc_cli_type__,)
    __ini_prc_config__=clsConfigEx(str_ini_file_name)
    
    __prc_cycletime=__ini_prc_config__.CycleTime.prc_cycletime
    __prc_expiretime=__ini_prc_config__.CycleTime.prc_expiretime
    __prc_healthytime=__ini_prc_config__.CycleTime.prc_healthytime
    
    # 取得ini文件中的全部声音资源列表
    # ToDo 自动遍历ini文件中，Sound字段下的配置文件
    dict_sound = {}
    dict_sound['reading_gr']= __ini_prc_config__.Sound.reading_gr
    dict_sound['reading_nr']= __ini_prc_config__.Sound.reading_nr
    dict_sound['reading_mr']= __ini_prc_config__.Sound.reading_mr
    dict_sound['check_ng']=__ini_prc_config__.Sound.check_ng
    
    # 增加Redis中总线程计数器，并将增加后的计数器值作为当前线程的id
    __prc_id__ = inst_redis.incrkey(f"pro_mon:prc_counter")
    
    inst_logger.info("线程 %s 取得 prc_id = %d, cli_id = %d"%(__prc_name__,__prc_id__,__cli_id__)) 
    inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
    inst_logger.info("线程 %s 已设置线程锁，过期时间 = %d ms"%(__prc_name__,__prc_expiretime)) 

    # 增加当前线程的重启次数,如为1说明是首次启动
    __prc_restart__ = inst_redis.incrkey(f"pro_mon:{__prc_name__}:restart")           ## manucal scan函数不记录重启 ##
    inst_logger.info("线程 %s 启动次数 restart = %d"%(__prc_name__,__prc_restart__))    ## manucal scan函数不记录重启 ##
        
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
    
    # 初始化pygame.mixer
    pygame.mixer.init()
    
    REST = inst_redis.xcreategroup("stream_test", __prc_name__)
    if REST :   # 返回值不为空，说明异常信息
        inst_logger.info("线程 %s 注册stream组失败，该组已存在， %s " %(__prc_name__, REST))
        for i, e in enumerate(inst_redis.lstException):
            inst_logger.error(
                "线程 %s 运行过程中发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                % (__prc_name__,e['module'], e['timestamp'], e['msg']))
        inst_redis.lstException.clear()
    else:
        inst_logger.info("线程 %s 注册stream组成功, %s " %(__prc_name__,REST))


    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
        
        # --------------------
        # 主线程操作区
        
        lst_reading_nr = list(inst_redis.getset("set_reading_nr"))  # 更新set_reading_nr
        set_reading_mr = inst_redis.getset("set_reading_mr")        # 更新set_reading_mr
        l = inst_redis.xreadgroup("stream_test",__prc_name__,"cliplay-id01")
        #if len(lst_reading_nr) + len(set_reading_mr) == 0:          # 正常状态，读取 stream_test, 每收到一个gr 播放一个声音l
        if len(l)>0:                                # 收到消息
            str_sysstatus = inst_redis.getkey("sys:status")
            inst_logger.info("收到序列 %s 中的消息累计 %d 行, 系统状态 %s " %(l[0][0],len(l[0][1]),str_sysstatus))
            for i,dictdata in l[0][1]:              # 遍历收到的所有消息
                if dictdata['result']=='GR':        # 正常识读
                    if str_sysstatus == "normal":
                        mixer.music.load(dict_sound['reading_gr'])
                        mixer.music.play()
                elif dictdata['result']=='MR':      # 多条码
                    mixer.music.load(dict_sound['reading_mr'])
                    mixer.music.play()
                elif dictdata['result']=='NR':      # 无条码
                    mixer.music.load(dict_sound['reading_nr'])
                    mixer.music.play()
                elif dictdata['result'][0:2] == 'NG': # 拒绝条码
                    mixer.music.load(dict_sound['check_ng'])
                    mixer.music.play()
        else:                                                       # 补码状态，收取HIK的读码信息，但是不播放声音，只播放补码声音
            pass
            

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
        if int_len_lst > 100:
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
        prc_run_lock=inst_redis.getkey(f"sys:cli{__cli_id__:02}:command")
        if prc_run_lock == "exit":
            inst_logger.info("线程 %s 已收到退出信号" %(__prc_name__,))
            inst_redis.xdelgroup("stream_test", __prc_name__)
            inst_logger.info("线程 %s 删除stream组成功" %(__prc_name__,))
            for i, e in enumerate(inst_redis.lstException):
                inst_logger.error(
                    "线程 %s 受控退出时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                    % (__prc_name__,e['module'], e['timestamp'], e['msg']))
            inst_redis.lstException.clear()
            # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
            # 如有则暂缓退出，如没有立即退出
            int_exit_code = 2           
            break
    inst_redis.clearkey(f"pro_mon:{__prc_name__}:run_lock")
    inst_logger.info("线程 %s 已退出，返回代码为 %d" %(__prc_name__,int_exit_code))

