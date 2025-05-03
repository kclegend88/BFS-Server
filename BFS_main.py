# -*- coding: utf-8 -*-
import sys
# sys.path.append("../..")
sys.path.append("include")
sys.path.append("prc")
import datetime
import os
import psutil
import time
import traceback
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from include.fLog import clsLogger
from include.fConfig import clsConfig
from include.fRedis import clsRedis
#from prc_stmP import start_process as start_stmP
#from prc_stmC import start_process as start_stmC
from prc.prc_HIKCamera import start_process as start_HIKCamera
from prc.prc_PLC import start_process as start_PLC
from prc.prc_stmHIKC_data import start_process as start_stmHIKC_data
from prc.prc_stmManualScan import start_process as start_stmManualScan
from prc.prc_stmReadingConfirm import start_process as start_stmReadingConfirm
from prc.prc_monitor_new import start_process as start_monitor
from prc.prc_stmHIKC_file import start_process as start_stmHIKC_file
from prc.prc_stmHIKC_file_2 import start_process as start_stmHIKC_file_2
from prc.prc_BarcodeCheck import start_process as start_BarcodeCheck
from prc.prc_stmReadingConfirm_dss import start_process as start_stmReadingConfirm_dss


class main:
    def __init__(self):
        # 仅初始化所有变量，禁止在此执行可能报错的语句
        self.__version__='1.0.0'
        self.status = 0       # 初始化运行状态
        # 定义线程总表，所有在该表格中的线程由main启动并监控
        # self.lst_thread_name = ["HIKCamera","stmHIKC_data","stmReadingConfirm","stmManualScan","PLC", "stmHIKC_file", "stmHIKC_file_2", "BarcodeCheck"]
        self.lst_thread_name = ["HIKCamera", "stmHIKC_data", "stmReadingConfirm", "stmManualScan", "PLC", "stmHIKC_file", "stmHIKC_file_2", "BarcodeCheck", "stmReadingConfirm_dss"]
        self.ini_config = None
        self.inst_logger = None
        self.inst_redis = None
        self.lst_thread = []
        self.prc_mon_thread = None

    def run(self):
        # 创建配置ini、log、redis实例
        ini_config = clsConfig('BFS_main.ini')
        self.inst_logger = clsLogger(ini_config)
        self.inst_redis = clsRedis(ini_config)
        self.inst_logger.info("main 线程启动")

        # 读取配置文件
        try:
            __device_name__= ini_config.Name.Device_Name
        except:
            self.inst_logger.error("配置读取失败"+traceback.format_exc())
            input("从ini文件中读取配置信息失败,请按任意键....")
            self.status = 127               # 无配置文件退出
            return

        self.status = 126  # 读取配置文件成功，状态为 126
        self.inst_logger.info("配置与日志初始化成功")

        # 尝试连接Redis
        try:
            self.inst_redis.connect(ini_config)
            if self.inst_redis.lstException:  # 取得异常消息队列中的信息
                for i, e in enumerate(self.inst_redis.lstException):
                    self.inst_logger.error(
                        "主线程连接 Redis 服务器失败，调用模块 %s，调用时间 %s，异常信息 %s "
                        % (e['module'], e['timestamp'], e['msg']))
                self.inst_redis.lstException.clear()
                return               # Redis 连接失败
            self.status = 125  # Redis 连接成功，状态为 125
            self.inst_logger.info("Redis 连接成功")

            main_prc_running = self.inst_redis.getkey(f"sys:ready")
            if main_prc_running == "true":
                # 其他main线程正在运行中，强制退出
                self.inst_logger.error("已有程序运行中，本程序将退出！！！")
                return              # 有实例运行导致退出

            self.status = 124  # 单一实例查询成功，状态为 124
            self.inst_logger.info("单一实例确认成功")

        except Exception as e:
            self.inst_logger.error("Redis连接过程中发生异常:"+traceback.format_exc())
            return               # Redis 连接过程中发生异常（连接失败、有实例运行、数据清理失败等）
        
        self.inst_redis.setkey(f"sys:ready", "true") # 向Redis标注主程序已运行
        self.status = 122  # 实例注册成功，状态为 122
        # 所有线程启动前，系统进入idle状态
        # 如果[PLC_Config] StartConv = True 则会在线程启动后自动启动输送机并进入normal状态
        self.inst_redis.setkey(f"sys:status","idle")
        
        # 尝试启动线程
        try:
            # 遍历线程总表 逐个启动线程
            for i,str_prc_name in enumerate(self.lst_thread_name):
                str_thread_name = "start_%s" %(str_prc_name,)               # 每个线程的start_process 需在import中 定义为start_ + 线程名称
                self.inst_logger.info("主程序尝试启动线程: %s" %(str_thread_name,)) # 通过globlas().get 取得指定名称的入口句柄 返回给Thread作为线程启动入口
                thread = threading.Thread(target=globals().get(str_thread_name), args=(ini_config,),name=str_prc_name)
                thread.start()                  # 启动线程
                                                # ToDo 需加入判断线程是否成功启动的代码
                time.sleep(1)               
                self.lst_thread.append(thread)       # 加入线程列表
            self.inst_logger.info("主程序已尝试启动全部线程，共计 %d 个" % (len(self.lst_thread_name),))
            self.status = 100  # 全部线程已通知启动，状态为 100
        except Exception as e:
            self.inst_logger.error ("线程启动失败"+traceback.format_exc())
            return             # 启动线程时发生异常


        # 启动监控线程
        self.prc_mon_thread = threading.Thread(target=globals().get("start_monitor"), args=(ini_config,self.lst_thread),name="start_monitor")
        self.prc_mon_thread.start()
        self.inst_logger.info("监控线程已启动")
        
        # 打印所有线程名称
        th_count = 0
        for i,th in enumerate(self.lst_thread):
            self.inst_logger.info("当前在线线程 编号 %d,线程名称 %s"%(i+1,th.getName()))
            th_count = th_count + 1
            # print(th.getName())
        if th_count:
            self.inst_logger.info("累计成功启动线程 %d 个" % (th_count,))
        time.sleep(3)
        
        self.inst_redis.setkey("sys:batchid","##")      # 初始化MAWB

    def stop_main(self, op):
        op.inst_redis.setkey("pro_mon:monitor:command", "exit")
        # 查找所有cli，通知所有已经启动的main_cli，自行退出
        cli_list = op.inst_redis.keys("sys_cli")
        for i, str_cli in enumerate(cli_list):
            if str_cli.endswith(":ready"):
                op.inst_redis.clearkey(str_cli)  # 删除所有sys_cli下面 以:ready结尾的键
                op.inst_logger.info("主程序清理服务端键值 %d " % (str_cli,))

        # 将主程序堵塞至所有线程全部完成
        for i, th in enumerate(op.lst_thread):
            th.join()
        op.prc_mon_thread.join()

        # 清理主线程的单一实例锁
        op.inst_redis.setkey(f"sys:ready", "false")
        op.inst_logger.info("sys:ready 已清除")
        # 退出时应清理主线程运行标志
        if op.status < 123:
            op.inst_redis.setkey(f"sys:ready", "false")


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BFS_Monitor")
        self.main_instance = None
        self.redis_conn = None
        self.setup_ui()
        self.after(1000, self.update_status)
        self.app = None
        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        # 添加状态标签
        self.status_label = ttk.Label(self, text="")
        self.status_label.pack()

    def setup_ui(self):
        self.tree = ttk.Treeview(self, columns=('ID', '线程名', '最后更新时间', '状态'), show='headings')
        self.tree.heading('ID', text='ID')
        self.tree.heading('线程名', text='Thread')
        self.tree.heading('最后更新时间', text='Last_Update_Time')
        self.tree.heading('状态', text='Status')
        
        # 配置列宽
        self.tree.column('ID', width=50, anchor='center')
        self.tree.column('线程名', width=150, anchor='w')
        self.tree.column('最后更新时间', width=200, anchor='center')
        self.tree.column('状态', width=100, anchor='center')
        
        self.tree.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start_process)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_process)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.init_open()
        
    def init_open(self):
        if self.redis_conn is None:
            self._init_redis()
        pid = self.redis_conn.getkey(f"sys:pid")
        if pid:
            pid = int(pid)
            for proc in psutil.process_iter(['pid']):
                try:
                    if proc.info['pid'] == pid:
                        self.show_error_dialog("There is currently a program that has not been closed. Please close the program and restart it!")
                        sys.exit(300)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # 处理进程不存在或权限不足的情况
                    pass
        try:
            print(f"PID 已更新为当前进程: {os.getpid()}")
            self.redis_conn.setkey(f"sys:pid", os.getpid())
            # print(f"PID 已更新为当前进程: {os.getpid()}")
        except Exception as e:
            # print(f"更新 Redis PID 失败: {e}")
            sys.exit(300)

    def start_process(self):
        if self.main_instance and self.main_instance.is_alive():
            return
        self.main_instance = threading.Thread(target=self.run_main)
        self.main_instance.start()

    def run_main(self):
        try:
            if self.redis_conn is None:
                self._init_redis()
            self.redis_conn.flushall()
            try:
                print(f"PID 已更新为当前进程: {os.getpid()}")
                self.redis_conn.setkey(f"sys:pid", os.getpid())
                # print(f"PID 已更新为当前进程: {os.getpid()}")
            except Exception as e:
                # print(f"更新 Redis PID 失败: {e}")
                sys.exit(300)
        except Exception as e:
            print("Redis初始化失败:", traceback.format_exc())
        self.app = main()
        self.app.run()

    def stop_process(self):
        main().stop_main(self.app)

    def update_status(self):
        if self.redis_conn is None:
            self._init_redis()

        current_time = time.time()
        i = 0
        for name in main().lst_thread_name + ["monitor"]:
            i += 1
            lu_ts_str = self.redis_conn.getkey(f"pro_mon:{name}:lu_ts") if self.redis_conn else None
            try:
                # 尝试解析各种时间格式
                lu_ts = datetime.datetime.fromisoformat(lu_ts_str.replace("Z", "+00:00")).timestamp()
            except:
                lu_ts = 0
            status = "RUN" if lu_ts and (current_time - lu_ts) < 5 else "EXIT"
            last_update = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(lu_ts))) if lu_ts else "N/A"

            items = self.tree.get_children()
            exists = any(self.tree.item(item)['values'][1] == name for item in items)

            if not exists:
                self.tree.insert('', 'end', values=(i, name, last_update, status))
            else:
                for item in items:
                    if self.tree.item(item)['values'][1] == name:
                        self.tree.item(item, values=(i, name, last_update, status))

        self.update_buttons_state()
        self.after(1000, self.update_status)

    def _init_redis(self):
        try:
            config = clsConfig('BFS_main.ini')
            self.redis_conn = clsRedis(config)
            self.redis_conn.connect(config)
            if self.redis_conn.lstException:  # 取得异常消息队列中的信息
                for i, e in enumerate(self.redis_conn.lstException):
                    self.inst_logger.error(
                        "主线程连接 Redis 服务器失败，调用模块 %s，调用时间 %s，异常信息 %s "
                        % (e['module'], e['timestamp'], e['msg']))
                self.redis_conn.lstException.clear()
                return               # Redis 连接失败
        except Exception as e:
            print("Redis初始化失败:", traceback.format_exc())
            self.show_error_dialog("Redis connection error!")
            sys.exit(300)
            

    def update_buttons_state(self):
        if self.redis_conn is None:
            self._init_redis()

        all_stopped = True
        if self.redis_conn:
            for name in main().lst_thread_name + ["monitor"]:
                lu_ts_str = self.redis_conn.getkey(f"pro_mon:{name}:lu_ts")
                try:
                    # 尝试解析各种时间格式
                    lu_ts = datetime.datetime.fromisoformat(lu_ts_str.replace("Z", "+00:00")).timestamp()
                except:
                    lu_ts = 0
                if lu_ts and (time.time() - float(lu_ts)) < 10:
                    all_stopped = False
                    break

        self.start_btn['state'] = tk.NORMAL if all_stopped else tk.DISABLED
        self.stop_btn['state'] = tk.DISABLED if all_stopped else tk.NORMAL
        
    def show_error_dialog(self, message):
        """显示错误弹窗（必须在主线程调用）"""
        messagebox.showerror("Error", message)
        
    def on_close(self):
        """处理窗口关闭事件"""
        if messagebox.askokcancel("Exit", "Are you sure you want to exit the program?"):
            # 禁用按钮防止重复操作
            self.start_btn['state'] = tk.DISABLED
            self.stop_btn['state'] = tk.DISABLED
            self.status_label.config(text="Stopping threads, please wait...")
            
            # 启动后台线程执行停止操作
            threading.Thread(target=self.async_stop_and_exit, daemon=True).start()

    def async_stop_and_exit(self):
        """异步停止线程并退出"""
        # 执行停止操作
        if hasattr(self, 'app') and self.app:
            self.stop_process()
        
        # 在UI线程执行清理
        self.after(0, self.cleanup_and_exit)

    def cleanup_and_exit(self):
        """清理资源并关闭窗口"""
        self.status_label.config(text="")
        self.destroy()
        
        # 确保完全退出程序
        os._exit(0)
        

if __name__ == '__main__':
    app = MainApp()
    app.mainloop()