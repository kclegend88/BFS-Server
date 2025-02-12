# -*- coding: utf-8 -*-
"""
    封装log配置
"""

import logging
from fConfig import clsConfig
from logging.handlers import RotatingFileHandler


class clsLogger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(clsLogger, cls).__new__(cls)
            cls._instance.init(*args, **kwargs)
        return cls._instance

    def init(self, config: clsConfig):
        try:
            iniConfig = config
            # 日志参数
            log_level = iniConfig.Log_Config.Log_Level  # 日志级别
            log_Filename = iniConfig.Log_Config.Log_Filename  # 日志文件名
            log_Size = iniConfig.Log_Config.Log_Size  # 日志文件大小
            log_Count = iniConfig.Log_Config.Log_Count  # 备份数量
            # 配置参数
            deviceName = iniConfig.Name.Device_Name  # 设备名称
            
            # 创建文件handler
            # ToDo:调试发现，如目录或文件不存在，会报错并退出，无法自行创建;后续需加入自动创建代码
            file_handler = RotatingFileHandler(log_Filename, maxBytes=log_Size, backupCount=log_Count,
                                          encoding='utf-8')  # 文件路径/文件名，最大大小，备份数量
            # 创建屏幕handler
            screen_hanlder = logging.StreamHandler()
            
            # 创建日志格式器
            # 级别 设备名称 时间  线程  调用类  行号  内容
            # [ERROR] [xx.xx.xx.xx] 2024-05-12 12:12:47 [catalina-exec-20] [com.hikvision.wms.debug：139] [UPDATE]- 服务器连接失败==> Data- [] [Result:NO]- [连接失败原因：404] ==>DEVICE NAME
            file_log_format = f"__[%(levelname)s]_[{deviceName}]_[%(asctime)s]_[%(threadName)s]_[%(filename)s/%(module)s.%(lineno)d]_%(message)s__"
            file_formatter = logging.Formatter(file_log_format)
            file_handler.setFormatter(file_formatter)
            
            # 20241215 Update screen format
            #[thread] TS level: Message
            screen_log_format = f"[%(threadName)s] %(asctime)s %(levelname)s : %(message)s([%(filename)s/%(module)s.%(lineno)d])"
            screen_formatter = logging.Formatter(screen_log_format)
            screen_hanlder.setFormatter(screen_formatter)

            # 创建 Logger 对象
            self.logger = logging.getLogger()

            # 设置日志级别
            self.logger.setLevel(log_level)

            # 将文件处理器添加到 Logger 对象
            self.logger.addHandler(file_handler)
            
            # 将屏幕处理器添加到 logger 对象
            self.logger.addHandler(screen_hanlder)
        except Exception as e:
            print("发生错误", e)

    def debug(self,  message):
        self.logger.debug(f"{message}",stacklevel=2)
        return True

    def info(self,  message):
        self.logger.info(f"{message}",stacklevel=2)
        return True

    def warning(self,  message):
        self.logger.warning(f"{message}",stacklevel=2)
        return True

    def error(self,  message):
        self.logger.error(f"{message}",stacklevel=2)
        return True

    def get_logger(self):
        return self.logger
'''
    def info(self, operation, message, data, result, o_object):
        self.logger.info(f"[{operation}]_[{message}]_[{data}]_[{result}]_[{o_object}]")
        return True

    def warning(self, operation, message, data, result, o_object):
        self.logger.warning(f"[{operation}]_[{message}]_[{data}]_[{result}]_[{o_object}]")
        return True

    def error(self, operation, message, data, result, o_object):
        self.logger.error(f"[{operation}]_[{message}]_[{data}]_[{result}]_[{o_object}]")
        return True
'''

