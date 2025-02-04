# prc_template  v 0.3.0
import json
import os
import shutil
import threading
import time
from datetime import datetime

from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis
from fHIKCamera import clsHIKCameraClient


def start_process(config_file):
    __prc_name__ = "stmHIKC_file"  ### 需手动配置成线程名称

    ini_config = clsConfig(config_file)  # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)  # 实际上与主线程使用的是同一实例
    inst_redis = clsRedis(ini_config)  # 实际上与主线程使用的是同一实例

    inst_logger.info("线程 %s 正在启动" % (__prc_name__,))

    # 本地ini文件读取
    str_ini_file_name = "prc_%s.ini" % (__prc_name__,)
    __ini_prc_config__ = clsConfigEx(str_ini_file_name)
    __prc_cycletime = __ini_prc_config__.CycleTime.prc_cycletime
    __prc_expiretime = __ini_prc_config__.CycleTime.prc_expiretime
    __prc_healthytime = __ini_prc_config__.CycleTime.prc_healthytime

    # --------------------    
    # 定制化配置参数读取区
    # HIK图片位置
    AIRead_path = __ini_prc_config__.extract_File.AIRead_path
    ErrRead_path = __ini_prc_config__.extract_File.ErrRead_path
    NoRead_path = __ini_prc_config__.extract_File.NoRead_path
    # 存储图片位置
    AITarget_path = __ini_prc_config__.target_File.AITarget_path
    ErrTarget_path = __ini_prc_config__.target_File.ErrTarget_path
    NoTarget_path = __ini_prc_config__.target_File.NoTarget_path
    # 定制化配置参数读取区
    # --------------------

    # 系统将初始化信息写入Redis
    __prc_id__ = inst_redis.init_prc(__prc_name__, __prc_expiretime)
    if not __prc_id__:  # 取得异常消息队列中的信息
        for i, e in enumerate(inst_redis.lstException):
            inst_logger.error(
                "线程 %s 注册 Redis 服务器失败，调用模块 %s，调用时间 %s，异常信息 %s "
                % (__prc_name__, e['module'], e['timestamp'], e['msg']))
        inst_redis.lstException.clear()
        return  # Redis 注册失败失败

    # --------------------    
    # 以下为定制初始化区域
    stream_name_create = "stream_test"
    stream_name_delete = "stream_reading_confirm"
    # 检查并创建消费组
    group_name = "stmHIKC_file"
    try:
        inst_redis.xcreategroup(stream_name_create, __prc_name__)
        inst_logger.info("线程 %s 注册stream组成功" % (__prc_name__,))
    except Exception as e:
        inst_logger.info("线程 %s 注册stream组失败，该组已存在" % (__prc_name__,))
    try:
        inst_redis.xcreategroup(stream_name_delete, __prc_name__)
        inst_logger.info("线程 %s 注册stream组成功" % (__prc_name__,))
    except Exception as e:
        inst_logger.info("线程 %s 注册stream组失败，该组已存在" % (__prc_name__,))
    # 以上为定制初始化区域           
    # --------------------    

    # 主线程变量初始化：启动变量，退出返回值
    b_thread_running = True
    int_exit_code = 0

    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock", __prc_id__, __prc_expiretime)
        # --------------------
        # 以下为主线程操作区
        # 获取stream_test，stream_reading_confirm
        stream_test = inst_redis.xreadgroup(stream_name_create, group_name, "consumer1")
        if stream_test:
            inst_logger.info("收到创建序列 %s 中的消息累计 %d 行" % (stream_test[0][0], len(stream_test[0][1])))
            for i, dictdata in stream_test[0][1]:  # 遍历收到的所有消息
                uid = dictdata['uid']  # 正常识读
                result = dictdata['result']
                inst_logger.info(f"获取到UID:{uid},result={result}")
                if uid is None or result is None:
                    continue
                if result == 'GR':
                    path = AIRead_path
                    order_path = AITarget_path
                elif result == 'NR':
                    path = NoRead_path
                    order_path = NoTarget_path
                elif result == 'MR':
                    path = ErrRead_path
                    order_path = ErrTarget_path
                    uid = uid[:-2]
                else:			# 对于其他场景，比如NG，暂时使用默认的GR目录
                    path = AIRead_path
                    order_path = AITarget_path
                # 用uid去指定文件夹下获取对应的图片
                # 先构建 图片路径 获取当前日期
                now = datetime.now()
                day = now.strftime("%Y-%m-%d")

                path = path + '\\' + day + '\\'
                order_path = order_path + '\\' + day + '\\'
                print(path)
                print(order_path)
                # 查找包含uid的图片
                if os.path.exists(path):
                    # 获取文件及其最后修改时间，按修改时间排序
                    files = [(filename, os.path.getmtime(os.path.join(path, filename))) for filename in
                             os.listdir(path)]
                    # 按修改时间排序，降序排列（最近的文件排前面）
                    files_sorted = sorted(files, key=lambda x: x[1], reverse=True)

                    # 遍历排序后的文件
                    for filename, _ in files_sorted:
                        inst_logger.info(f"正在遍历图片file:{filename},uid={uid}")
                        if uid in filename:  # 如果文件名中包含uid
                            inst_logger.info(f"图片已找到")
                            full_path = os.path.join(path, filename)
                            # 检查目标路径是否存在，如果不存在则创建
                            if not os.path.exists(order_path):
                                print("目标路径不存在，正在创建...")
                                os.makedirs(order_path)

                            # 构建目标路径文件名
                            target_file_path = os.path.join(order_path, filename)

                            # 复制图片到目标路径
                            shutil.copy(full_path, target_file_path)
                            inst_logger.info(f"图片复制成功")
                            break  # 如果只需要找到一个图片就可以退出循环
                        else:
                            inst_logger.info(f"当前图片不是，尝试下一张")
                else:
                    inst_logger.info(f"图片路径不存在")
        # 删除
        stream_delete = inst_redis.xreadgroup(stream_name_delete, group_name, "consumer1")
        if stream_delete:
            inst_logger.info("收到删除序列 %s 中的消息累计 %d 行" % (stream_delete[0][0], len(stream_delete[0][1])))
            for i, dictdata in stream_delete[0][1]:
                uid = dictdata['uid']
                scan_result = dictdata['scan_result']
                inst_logger.info(f"获取到UID:{uid},scan_result:{scan_result}")
                if uid is None or scan_result is None:
                    continue
                if "GR" in scan_result:
                    order_path = AITarget_path
                elif "NR" in scan_result:
                    order_path = NoTarget_path
                elif "MR" in scan_result:
                    order_path = ErrTarget_path
                    uid = uid[:-2]
                # 用uid去指定文件夹下获取对应的图片
                # 先构建 图片路径 获取当前日期
                now = datetime.now()
                day = now.strftime("%Y-%m-%d")
                order_path = order_path + '\\' + day + '\\'
                # 查找包含uid的图片
                if os.path.exists(order_path):
                    # 遍历目录中的所有文件
                    for filename in os.listdir(order_path):
                        if uid in filename:  # 如果文件名中包含uid
                            full_path = os.path.join(order_path, filename)
                            # 删除此图片
                            try:
                                # 删除此文件
                                os.remove(full_path)
                                print(f"图片 {filename} 已删除")
                            except Exception as e:
                                print(f"删除文件 {filename} 时发生错误: {e}")
        # 以上为主线程操作区       
        # --------------------
        time.sleep(__prc_cycletime / 1000.0)  # 所有时间均以ms形式存储

        # 线程运行时间与健康程度判断
        inst_redis.ct_refresh(__prc_name__)
        # ToDo

        # 线程是否继续运行的条件判断

        # 如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock = inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:
            # --------------------
            # 以下为定制区域，用于中止线程内创建的线程或调用的函数

            # 以上为定制区域，用于中止线程内创建的线程或调用的函数           
            # --------------------
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
