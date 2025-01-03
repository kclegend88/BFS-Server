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
from fHIKCamera import clsHIKCameraClient



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

    def prc_PLC_startconv(self):        # 启动输送机，只要command收到start 即执行
        nonlocal __inst_plc__,inst_redis,plc_conv_command,plc_conv_status,plc_conv_fullspeed
        if plc_conv_status == 'run' and plc_conv_fullspeed == 'yes': # 已启动，高速，记录逻辑错误
            inst_logger.error("线程 %s 高速时收到启动信号" % (__prc_name__,))
            inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行 
            return
        for i in range(1, 5):
            __inst_plc__.db_write(12, 3 + (i - 1) * 4, bytearray([3]))
        inst_redis.setkey(f"plc_conv:status", "run")
        inst_redis.setkey(f"plc_conv:fullspeed", "yes")
        for i in range(1, 5):
            inst_redis.setkey(f"plc_conv:CV0{i}:speed", "high")
        inst_logger.info("线程 %s 皮带机启动，当前速度为高速" % (__prc_name__,))
        inst_redis.clearkey('plc_conv:command')             # 执行后删除command,确保执行一次

    def prc_PLC_stopconv(self):         # 停止输送机，只要command收到stop 即执行
        nonlocal __inst_plc__,inst_redis,plc_conv_command,plc_conv_status,plc_conv_fullspeed
        if plc_conv_status == 'pause':  # 已停止，记录逻辑错误
            inst_logger.error("线程 %s 停止时收到停机信号" % (__prc_name__,))
            inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行            
            return       
        for i in range(1, 5):
            __inst_plc__.db_write(12, 3 + (i - 1) * 4, bytearray([0]))
        inst_redis.setkey("plc_conv:status", "pause")
        inst_redis.clearkey('plc_conv:fullspeed')
        for i in range(1, 5):
            inst_redis.setkey(f"plc_conv:CV0{i}:speed", "stop")
        inst_logger.info("线程 %s 皮带机停止，当前速度为0" % (__prc_name__,))
        inst_redis.clearkey('plc_conv:command') # 执行后删除command,确保执行一次

    # 补码线程一旦发现所有异常被消除就会发送autospeedup，输送机需根据当前状态判断是否执行；
    # 如果输送机已经高速了，说明软件设计的逻辑出现问题，
    # prc_PLC_autospeedup程序段应记录内部逻辑错
    def prc_PLC_autospeedup(self):        
        nonlocal __inst_plc__,inst_redis,plc_conv_command,plc_conv_status,plc_conv_fullspeed
        if plc_conv_fullspeed == 'yes':             # 已高速，记录逻辑错误
            inst_logger.error("线程 %s 高速时收到加速信号" % (__prc_name__,))
            inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行             
            return
        for i in range(1, 5):
            __inst_plc__.db_write(12, 3 + (i - 1) * 4, bytearray([3]))
        inst_redis.setkey(f"plc_conv:status", "run")    
        inst_redis.setkey(f"plc_conv:fullspeed", "yes")         
        for i in range(1, 5):
            inst_redis.setkey(f"plc_conv:CV0{i}:speed", "high")
        inst_logger.info("线程 %s 皮带机从减速变为高速，当前速度为高速" % (__prc_name__,))
        inst_redis.clearkey('plc_conv:command') # 执行后删除command,确保执行一次
        
    # 读码线程一旦发现有NR或MR就会判断输送机状态，如果输送机是高速运行，就会将fullspeed设置成countdown
    # 并发送slowndown指令；
    # 如果输送机执行slowndown指令时，发现输送机已经是低速或停机了，说明软件设计的逻辑出现问题，
    # prc_PLC_autoslowdown程序段应记录内部逻辑错误
    def prc_PLC_autoslowdown(self):         
        nonlocal __inst_plc__,inst_redis,plc_conv_command,plc_conv_status,plc_conv_fullspeed
        if plc_conv_status == 'run' and plc_conv_fullspeed == 'countdown':# 已减速，记录逻辑错误
            inst_logger.error("线程 %s 低速时收到减速信号" % (__prc_name__,))
            inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行            
            return     
        
        if plc_conv_status == 'pause' :     # 已停止，记录逻辑错误
            inst_logger.error("线程 %s 停止时收到减速信号" % (__prc_name__,))
            inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行            
            return          
        
        if not plc_conv_fullspeed:          # 系统已删除fullsped标志，但尚未停机时收到减速信号
            inst_logger.error("线程 %s 收到减速指令时发现应停止输送机" % (__prc_name__,))
            prc_PLC_autostop()              # 停机优先级大于减速,直接调用停机子函数
            inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行            
            return         
        inst_redis.setkey(f"plc_conv:fullspeed", "countdown")         
        __inst_plc__.db_write(12, 3, bytearray([0]))
        __inst_plc__.db_write(12, 7, bytearray([1]))
        __inst_plc__.db_write(12, 11, bytearray([1]))
        __inst_plc__.db_write(12, 15, bytearray([3]))
        inst_redis.setkey(f"plc_conv:CV01:speed", "stop")
        inst_redis.setkey(f"plc_conv:CV02:speed", "low")
        inst_redis.setkey(f"plc_conv:CV03:speed", "low")
        inst_redis.setkey(f"plc_conv:CV04:speed", "high")
        inst_logger.info("线程 %s 皮带机减速，当前速度为降速" % (__prc_name__,))   
        inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行   
    # PLC线程一旦发现fullspeed消失，说明countdown时间已经超过设定值，
    # 或PLC线程发现有NR、MR的包裹没有被消除状态就流出CV03，或CV03上异常数量超过3个
    # PLC线程会自己调用 prc_PLC_autostop() 直接停止输送机 
    # 如果调用时发现输送机处于高速，或者已经停机，说明软件设计的逻辑出现问题，
    # prc_PLC_autostop程序段应记录内部逻辑错误
    def prc_PLC_autostop(self):         # 自动降速，根据fullspeed过期及当前状态，决定是否执行
        nonlocal __inst_plc__,inst_redis,plc_conv_command,plc_conv_status,plc_conv_fullspeed
        if plc_conv_status == 'run' and plc_conv_fullspeed == 'yes': # 高速，记录逻辑错误
            inst_logger.error("线程 %s 高速时收到自动停止信号" % (__prc_name__,))
            inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行 
            return
        
        if plc_conv_status == 'pause' :     # 已停止，记录逻辑错误
            inst_logger.error("线程 %s 停止时收到自动停止信号" % (__prc_name__,))
            inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行     
            return

        __inst_plc__.db_write(12, 3, bytearray([0]))
        __inst_plc__.db_write(12, 7, bytearray([0]))
        __inst_plc__.db_write(12, 11, bytearray([0]))
        __inst_plc__.db_write(12, 15, bytearray([3]))
        inst_redis.setkey(f"plc_conv:CV01:speed", "stop")
        inst_redis.setkey(f"plc_conv:CV02:speed", "stop")
        inst_redis.setkey(f"plc_conv:CV03:speed", "stop")
        inst_redis.setkey(f"plc_conv:CV04:speed", "high")            
        inst_redis.setkey("plc_conv:status", "pause")
        inst_logger.info("线程 %s 皮带机从降速到停止，当前速度为0" % (__prc_name__,))    
        inst_redis.clearkey('plc_conv:command') # 报错后删除command,避免重复执行   
    # 如果输送机在正常运转，每个周期根据输送机高速还是低速计算包裹前进的距离
    # 如果包裹离开CV03，将正常包裹信息填入stream reading confirm, 等待后续的一系列数据处理
    # 如果是异常包裹，则直接停线，只有重新start才可以开始继续扫描
    def prc_PLC_parcelposcalc(self):
        nonlocal __inst_plc__,inst_redis,__ini_conv_length
        plc_conv_status = inst_redis.getkey("plc_conv:status")
        plc_conv_fullspeed = inst_redis.getkey("plc_conv:fullspeed")

        if plc_conv_status == "pause":      # 如果输送机没有运转，不需要做任何计算
            return
        if plc_conv_fullspeed == 'yes':
            speed_x = __ini_speed_H
        elif plc_conv_fullspeed == 'countdown':
            speed_x = __ini_speed_L
        
        lst_parcel_keys=inst_redis.keysbuf('parcel:posx:')
        dict_reading_con ={}
        for i,key in enumerate(lst_parcel_keys):
            inst_redis.incrkey(f"{key}", incrby = speed_x)
            if int(inst_redis.getkey(f"{key}")) < __ini_conv_length:
                continue
            # posx已经大于 ini conv length, 流出CV03了
            lst_splited_keys = key.split(':')   # parcel:posx:<uid>
            str_uid = lst_splited_keys[-1]      # 取得uid
            str_result = inst_redis.getkey(f"parcel:scan_result:{str_uid}")
            str_barcode = inst_redis.getkey(f"parcel:barcode:{str_uid}")

            if not str_result in ['GR','MR_MS','NR_MS']:    # 有异常包裹流出
               inst_logger.error(f"异常包裹流出CV03！！ ,uid={str_uid},barcode={str_barcode},result={str_result}") 
               # 发送停线指令
               inst_redis.setkey(f"plc_conv:command", "stop")
               continue
            # 包裹正常流出
            dict_reading_con['uid'] = str_uid
            dict_reading_con['ts'] = datetime.datetime.now().isoformat()
            dict_reading_con['barcode'] = str_barcode
            dict_reading_con['scan_result'] = str_result
            # dict_reading_con['check_result'] = inst_redis.getkey(f"parcel:check_result:{str_uid}")
            # dict_reading_con['remark'] = inst_redis.getkey(f"parcel:remark:{str_uid}")                   

            inst_redis.xadd( "stream_reading_confirm", dict_reading_con)      # 插入stream
            # 清理redis中CV03上的包裹信息
            inst_redis.clearkey(f"{key}")
            inst_redis.clearkey(f"parcel:posy:{str_uid}")
            inst_redis.clearkey(f"parcel:sid:{str_uid}")
            inst_redis.clearkey(f"parcel:scan_result:{str_uid}")
            inst_redis.clearkey(f"parcel:barcode:{str_uid}")
            # inst_redis 
            inst_logger.debug(f"包裹已经离开CV03,uid={str_uid},barcode={str_barcode}") 

    __prc_name__="PLC"                      ### 需手动配置成线程名称
    
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

    # 获取PLCIP地址，DB大小
    __plc_ip__ = __ini_prc_config__.Sever.PLC_server_ip
    __plc_db_size = __ini_prc_config__.plc_info.DB3_size

    # 读取ini中 ini_speed_H， ini_speed_L， ini_conv_length
    __ini_speed_H = __ini_prc_config__.plc_info.ini_speed_H
    __ini_speed_L = __ini_prc_config__.plc_info.ini_speed_L
    __ini_conv_length = __ini_prc_config__.plc_info.ini_conv_length
    
    __ini_start_conv = __ini_prc_config__.Config.StartConv
 
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
    __inst_plc__ = snap7.client.Client()

    # 连接PLC
    inst_logger.info(f"线程{__prc_name__}尝试连接 PLC")
    PLC_connect(inst_logger, __inst_plc__, __plc_ip__)
    # command，status，cv1-cv4变量初始化
    # inst_redis.setkey("plc_conv:command", "stop")
    inst_redis.setkey(f"plc_conv:status", "pause")
    inst_redis.clearkey(f"plc_conv:fullspeed")
    inst_redis.setkey(f"plc_conv:CV01:speed", "stop")
    inst_redis.setkey(f"plc_conv:CV02:speed", "stop")
    inst_redis.setkey(f"plc_conv:CV03:speed", "stop")
    inst_redis.setkey(f"plc_conv:CV04:speed", "stop")
    inst_logger.info("线程 %s 在redis中变量初始化完成" % (__prc_name__,))
   
    if __ini_start_conv:            #根据配置文件决定，是否直接启动输送机
        inst_redis.setkey("plc_conv:command","start")
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
        # 刷新PLC 状态
        plc_conv_command = inst_redis.getkey("plc_conv:command")
        plc_conv_status = inst_redis.getkey("plc_conv:status")
        plc_conv_fullspeed = inst_redis.getkey("plc_conv:fullspeed")
        
        # 输送机强制启动，命令来自于外部客户端或main启动时的指令
        if plc_conv_command == "start":    
            prc_PLC_startconv()
        
        # 输送机强制停止，命令来自于外部客户端或main退出时的指令
        if plc_conv_command == "stop":      
            prc_PLC_stopconv()
        
        # 输送机自动减速，来自读码线程
        if plc_conv_command == "autoslowdown":  
            prc_PLC_autoslowdown()

        # 输送机自动加速，来自补码线程
        if plc_conv_command == "autospeedup":
            prc_PLC_autospeedup()
        
        # 输送机自动停止，来自PLC本线程
        if not plc_conv_fullspeed:
            prc_PLC_autostop()
            
        # 以上为主线程操作区       
        # --------------------
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        
        # 线程运行时间与健康程度判断
        inst_redis.ct_refresh(__prc_name__)
       
        # 根据输送机速度计算包裹位置，判断包裹是否离开CV03
        
        # 线程是否继续运行的条件判断
        
        #如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:  
            # --------------------
            # 以下为定制区域，用于中止线程内创建的线程或调用的函数

            # 以上为定制区域，用于中止线程内创建的线程或调用的函数           
            # --------------------
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

