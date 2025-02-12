# -*- coding: utf-8 -*-

import configparser
import os


class SectionConfigEx:
    def __init__(self, section):
        self._section = section

    def __getattr__(self, name):
        if name in self._section:
            value = self._section[name]
            try:
                return eval(value)  # 尝试转换
            except ValueError:
                return value  # 返回原始字符串值
        else:
            raise AttributeError(f"没有这样的属性: {name}")

    def __getitem__(self, name):
        if name in self._section:
            value = self._section[name]
            try:
                return eval(value)  # 尝试转换
            except ValueError:
                return value  # 返回原始字符串值
        else:
            raise KeyError(f"没有这样的键: {name}")



class clsConfigEx:
    
    #def __new__(cls, *args, **kwargs):
    #    cls._instance = super(clsConfigEx, cls).__new__(cls)
    #    cls._instance.init(*args, **kwargs)
    #    return cls._instance
        
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.read(self.config_file)

    def read(self, config_file):
        if not os.path.exists(config_file):
            raise FileNotFoundError

        self.config.read(config_file, encoding="utf-8")
        if not self.config.sections():
            raise Exception("配置文件为空，请检查配置文件！")
        # 动态生成属性
        for section_name in self.config.sections():
            setattr(self, section_name, SectionConfigEx(self.config[section_name]))

        # 界面显示：读取xx\xx\xxx\config.ini成功，


