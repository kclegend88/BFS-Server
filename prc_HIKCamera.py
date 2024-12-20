# prc_template  v 0.2.0
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
    __prc_name__="HIKCamera"
    
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
    # 定义相机连接参数
    __prc_tcp_ip = __ini_prc_config__.Network.Barcode_Reading_IP
    __prc_tcp_port = __ini_prc_config__.Network.Barcode_Reading_Port

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
    # inst_redis.connect()fg
    b_thread_running = True
    int_exit_code = 0
    # First_Connect = True
    
    cli = clsHIKCameraClient(__prc_tcp_ip, __prc_tcp_port)
    heart_luts= datetime.datetime.now()
    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
        
        # --------------------
        # 主线程操作区
        # 判断是否已连接，如未连接，尝试连接一次，连接不上就转下个循环
        if cli.bDISCONNECT:
            try:
                if connect_result = cli.connect():
                    inst_logger.info("线程 %s 连接相机成功,IP= %s, Port= %s,结果 %s"%(__prc_name__,__prc_tcp_ip,__prc_tcp_port,connect_result))
                    cli.start_recv_thread()
                    inst_logger.info("线程 %s 监听线程启动成功"%(__prc_name__,))
                else:
                    inst_logger.error("线程 %s 连接相机失败 %s"%(__prc_name__,))
            except Exception as e:
                inst_logger.error("线程 %s 尝试连接时发生错误,错误说明: %s"%(__prc_name__,e))

        # 如果已连接，尝试接收数据
        else:
            # 如果recv_buf不为空，说明recv线程接收到了数据
            if cli.recv_buf:
                # 处理接收到的数据
                # ToDo 报文解析子函数 对于格式不符、数据超过预期的报文进行报错
                # ToDo Redis 插入子函数，将数据插入stm,
                inst_logger.info("已收到报文 %s " %(cli.recv_buf,))               
                #清理缓冲区
                cli.recv_buf.clear()
            
            heart_current_ts = datetime.datetime.now() 
            td_heart_ct = heart_current_ts - heart_luts
            int_heart_ct = int(td_heart_ct.total_seconds())
            
            if int_heart_ct > 5:    # 这个数字今后要放到的ini里
                try:
                    heart_data = cli.heart()
                    cli.send(heart_data)
                    # inst_logger.debug("已发送心跳，报文为： %s" %(heart_data,))    
                except Exception as e:
                    cli.bDISCONNECT = True
                    inst_logger.error("线程 %s 尝试发送心跳时发生错误,错误说明: %s"%(__prc_name__,e))

        # 主线程操作区       
        # --------------------
        # inst_logger.debug("线程 %s 当前连接状态 %s"%(__prc_name__,not cli.bDISCONNECT))
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
            if not cli.bExit:
                cli.bShutdown = True    # 通知通讯线程 自我关闭
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
