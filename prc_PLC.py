# prc_template  v 0.2.0
import time
import datetime

import snap7

from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis


def start_process(config_file):
    __prc_name__ = "PLC"
    __inst_plc__ = snap7.client.Client()
    ini_config = clsConfig(config_file)  # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)
    inst_redis = clsRedis(ini_config)
    inst_logger.info("线程 %s 正在启动" % (__prc_name__,))

    # 本地ini文件存储的本线程专有配置参数
    # 定义线程循环时间、过期时间、健康时间等
    str_ini_file_name = "prc_%s.ini" % (__prc_name__,)
    __ini_prc_config__ = clsConfigEx(str_ini_file_name)

    __prc_cycletime = __ini_prc_config__.CycleTime.prc_cycletime
    __prc_expiretime = __ini_prc_config__.CycleTime.prc_expiretime
    __prc_healthytime = __ini_prc_config__.CycleTime.prc_healthytime

    # 获取PLCIP地址，DB大小
    __plc_ip__ = __ini_prc_config__.Sever.PLC_server_ip
    __plc_db_size = __ini_prc_config__.plc_info.DB3_size

    # 连接PLC
    inst_logger.info(f"线程{__prc_name__}尝试连接 PLC")
    PLC_connect(inst_logger, __inst_plc__, __plc_ip__)

    # 向Redis注册基本信息
    prc_run_lock = inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
    if prc_run_lock is None:
        # Redis中不存在该线程的运行锁，说明没有同名线程正在运行，无线程冲突，可以直接启动
        # 增加Redis中总线程计数器，并将增加后的计数器值作为当前线程的id
        __prc_id__ = inst_redis.incrkey(f"pro_mon:prc_counter")  # 线程数自动加一
        inst_logger.info("线程 %s 取得 id = %d" % (__prc_name__, __prc_id__))
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock", __prc_id__, __prc_expiretime)  # 增加线程锁，并设置过期时间
        inst_logger.info("线程 %s 已设置线程锁，过期时间 = %d ms" % (__prc_name__, __prc_expiretime))

        # 增加当前线程的重启次数,如为1说明是首次启动
        __prc_restart__ = inst_redis.incrkey(f"pro_mon:{__prc_name__}:restart")
        inst_logger.info("线程 %s 启动次数 restart = %d" % (__prc_name__, __prc_restart__))

        # 记录线程启动时间
        __prc_start_ts__ = datetime.datetime.now()
        inst_redis.setkey(f"pro_mon:{__prc_name__}:start_ts", __prc_start_ts__.isoformat())
        inst_logger.info("线程 %s 启动时间 start_ts= %s" % (__prc_name__, __prc_start_ts__.isoformat()))

        # 记录线程上次刷新时间，用于持续计算线程的cycletime
        prc_luts = __prc_start_ts__
        inst_redis.setkey(f"pro_mon:{__prc_name__}:lu_ts", prc_luts.isoformat())

        # 将当前线程加入Redis 线程集合中
        inst_redis.sadd("set_process", "name=%s/id=%d" % (__prc_name__, __prc_id__))
        inst_logger.info("线程 %s 已添加至线程集合中" % (__prc_name__,))

        # command，status，cv1-cv4变量初始化
        inst_redis.setkey("plc_conv:command", "stop")
        inst_redis.setkey(f"plc_conv:status", "pause")
        inst_redis.setkey(f"plc_conv:fullspeed", "Yes")
        inst_redis.setkey(f"plc_conv:CV01:speed", "stop")
        inst_redis.setkey(f"plc_conv:CV02:speed", "stop")
        inst_redis.setkey(f"plc_conv:CV03:speed", "stop")
        inst_redis.setkey(f"plc_conv:CV04:speed", "stop")
        inst_logger.info("线程 %s 在redis中变量初始化完成" % (__prc_name__,))

    else:
        # Redis中存在该线程的运行锁，说明已经有同名线程正在运行
        # 记录线程冲突错误并退出
        # ToDo 将此类重要错误 使用stm_sys_log进行永久化记录
        inst_logger.error("线程 %s 启动时发现了运行冲突,同名线程已存在,id= %d" % (__prc_name__, prc_run_lock))
        exit()

    b_thread_running = True
    int_exit_code = 0
    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock", __prc_id__, __prc_expiretime)

        # --------------------
        # 主线程操作区
        plc_conv_command = inst_redis.getkey("plc_conv:command")
        plc_conv_status = inst_redis.getkey("plc_conv:status")
        plc_conv_fullspeed = inst_redis.getkey("plc_conv:fullspeed")
        if plc_conv_command == "start" and plc_conv_status == "pause":
            # 启动所有皮带机 0 停止 1低速 2 低中速 3 4 修改redis中状态为高速
            for i in range(1, 5):
                __inst_plc__.db_write(12, 3 + (i - 1) * 4, bytearray([3]))
            inst_redis.setkey("plc_conv:status", "run")
            for i in range(1, 5):
                inst_redis.setkey(f"plc_conv:CV0{i}:speed", "high")
            inst_logger.info("线程 %s 皮带机启动，速度为高速" % (__prc_name__,))
        if plc_conv_command == "start" and plc_conv_status == "run":
            if plc_conv_fullspeed != "None":
                status = 0
                # 如果cv1-cv4 速度不为高速   则启动皮带机应为高速   降速状态到高速状态
                for i in range(1, 5):
                    if inst_redis.getkey(f"plc_conv:CV0{i}:speed") != 'high':
                        status = 1
                if status == 1:
                    for i in range(1, 5):
                        __inst_plc__.db_write(12, 3 + (i - 1) * 4, bytearray([3]))
                        inst_redis.setkey(f"plc_conv:CV0{i}:speed", "high")
                    inst_logger.info("线程 %s 已从低速变为高速" % (__prc_name__,))
            else:
                status = 0
                # 如果cv1-cv4 速度不为低速   则启动皮带机应为低速   高速状态变为低速状态
                if inst_redis.getkey(f"plc_conv:CV01:speed") == 'high' \
                        and inst_redis.getkey(f"plc_conv:CV02:speed") == 'high' \
                        and inst_redis.getkey(f"plc_conv:CV03:speed") == 'high' \
                        and inst_redis.getkey(f"plc_conv:CV04:speed") == 'high':
                    status = 1
                if status == 1:
                    inst_redis.setkey(f"plc_conv:CV01:speed", "stop")
                    inst_redis.setkey(f"plc_conv:CV02:speed", "low")
                    inst_redis.setkey(f"plc_conv:CV03:speed", "low")
                    inst_redis.setkey(f"plc_conv:CV04:speed", "high")
                    __inst_plc__.db_write(12, 3, bytearray([0]))
                    __inst_plc__.db_write(12, 7, bytearray([1]))
                    __inst_plc__.db_write(12, 11, bytearray([1]))
                    __inst_plc__.db_write(12, 15, bytearray([3]))
                    inst_logger.info("线程 %s 已从高速变为低速" % (__prc_name__,))
        if plc_conv_command == "stop" and plc_conv_status == "pause":
            pass
        if plc_conv_command == "stop" and plc_conv_status == "run":  # 正在运行，需要停线
            for i in range(1, 5):
                __inst_plc__.db_write(12, 3 + (i - 1) * 4, bytearray([0]))
                inst_redis.setkey(f"plc_conv:CV0{i}:speed", "stop")
            inst_redis.setkey("plc_conv:status", "pause")
            inst_logger.info("线程 %s 皮带已停线" % (__prc_name__,))
        # --------------------
        time.sleep(__prc_cycletime / 1000.0)  # 所有时间均以ms形式存储

        # 线程运行时间与健康程度判断

        current_ts = datetime.datetime.now()
        td_last_ct = current_ts - prc_luts  # datetime对象相减得到timedelta对象
        int_last_ct_ms = int(td_last_ct.total_seconds() * 1000)  # 取得毫秒数（int格式)

        prc_luts = current_ts  # 刷新luts
        inst_redis.setkey(f"pro_mon:{__prc_name__}:lu_ts", current_ts.isoformat())  # 更新redis中的luts

        inst_redis.lpush(f"lst_ct:%s" % (__prc_name__,), int_last_ct_ms)  # 将最新的ct插入redis中的lst_ct
        int_len_lst = inst_redis.llen(f"lst_ct:%s" % (__prc_name__,))  # 取得列表中元素的个数
        if int_len_lst > 10:
            inst_redis.rpop(f"lst_ct:%s" % (__prc_name__,))  # 尾部数据弹出
        # cycletime 计算 与 healthy判断
        # ToDo 

        # 线程是否继续运行的条件判断

        # 如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock = inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:
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


def PLC_connect(inst_logger, __inst_plc__, __plc_ip__):
    while True:
        __inst_plc__.connect(__plc_ip__, 0, 1)  # 连接到PLC
        if __inst_plc__.get_connected():
            inst_logger.error("线程 PLC PLC连接成功。")
            break
        else:
            inst_logger.error("线程 PLC PLC连接失败，三秒后重连")
        time.sleep(3)
