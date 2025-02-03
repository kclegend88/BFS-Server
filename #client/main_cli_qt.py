# prc_template  v 0.2.0
import sys
from symbol import pass_stmt

sys.path.append("include")
import re
from collections import deque
import os
import sys
import threading
import time
import datetime
import traceback
from ftplib import FTP

import pygame
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QSize, QThread
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QPalette, QBrush, QTransform
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication, QFrame, QLabel, QVBoxLayout, QSplitter, QHBoxLayout, \
    QTableWidgetItem, QLineEdit, QPushButton, QMessageBox,QStatusBar

from fBarcode import barcode_formatcheck
from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis
from pygame import mixer


class BarcodeDisplay(QWidget):
    def __init__(self, inst_redis, __cli_id__, inst_logger, __prc_name__, __ini_prc_config__):
        super().__init__()
        self.inst_redis = inst_redis
        self.__cli_id__ = __cli_id__
        self.inst_logger = inst_logger
        self.__prc_name__ = __prc_name__
        # 读取配置文件
        self.is_image = __ini_prc_config__.qt.image
        self.level = __ini_prc_config__.qt.level
        self.pic_direction = __ini_prc_config__.qt.pic_direction
        self.pic_rotate = __ini_prc_config__.qt.pic_rotate
        self.all_show_flag = __ini_prc_config__.qt.all_show_flag
        self.server_ip = __ini_prc_config__.qt.server_ip
        self.lst_re_exp = []
        self.lst_re_exp.append(__ini_prc_config__.Barcode.re_exp_01)
        self.lst_re_exp.append(__ini_prc_config__.Barcode.re_exp_02)
        # 存储图片位置
        self.AITarget_file_path = __ini_prc_config__.target_File.AITarget_path
        self.ErrTarget_path = __ini_prc_config__.target_File.ErrTarget_path
        self.NoTarget_path = __ini_prc_config__.target_File.NoTarget_path
        # ftp图片位置
        self.ftp_path_Alread = __ini_prc_config__.ftp_path.ftp_path_Alread
        self.ftp_path_Errread = __ini_prc_config__.ftp_path.ftp_path_Errread
        self.ftp_path_Noread = __ini_prc_config__.ftp_path.ftp_path_Noread
        self.barcode_input = ""  # 用来存储接收到的条码
        self.scanbarcode = ""
        # 创建数据流组
        self.stream_name_create = "stream_test"
        self.stream_name_delete = "stream_reading_confirm"
        # self.inst_logger.info("线程 %s 注册stream组成功" % (__prc_name__,))
        self.uid_deque = deque()  # 用来存储uid
        self.exception_list = []  # 存储异常时扫入的条码

        self.nofound_list = []
        # 局部初始变量
        self.exception_handling = 0
        try:
            inst_redis.xcreategroup(self.stream_name_create, self.__prc_name__)
            inst_logger.info("线程 %s 注册stream组 %s 成功" % (self.__prc_name__,self.stream_name_create))
        except Exception as e:
            inst_logger.info("线程 %s 注册stream组 %s 失败，该组已存在" % (self.__prc_name__,self.stream_name_create))
        try:
            inst_redis.xcreategroup(self.stream_name_delete, self.__prc_name__)
            inst_logger.info("线程 %s 注册stream组 %s 成功" % (self.__prc_name__,self.stream_name_delete))
        except Exception as e:
            inst_logger.info("线程 %s 注册stream组 %s 失败，该组已存在" % (self.__prc_name__,self.stream_name_delete))
        self.init_ui()

        # 清场模式下 扫描条码的集合已扫描数据集合
        self.scanned_gr = set()
        self.scanned_mr = set()
        self.scanned_nr = set()
        self.scanned_all = set()

        self.dict_sound = {}
        self.dict_sound['ms_barcode_reject'] = __ini_prc_config__.Sound.ms_barcode_reject
        self.dict_sound['ms_barcode_exist'] = __ini_prc_config__.Sound.ms_barcode_exist
        self.dict_sound['ms_barcode_rescan_accept'] = __ini_prc_config__.Sound.ms_barcode_rescan_accept

    def addImageToFrame(self, frame_name, i, barcode):
        # 使用对象名找到相应的 QFrame
        frame = self.findChild(QFrame, frame_name)
        if not frame:
            self.inst_logger.info(f"未找到名为 {frame_name} 的 QFrame")
            return

        # 加载图片
        image = QPixmap(f"{i}")  # i 是图片的路径
        if image.isNull():
            self.inst_logger.info(f"图片路径 {i} 无效")
            return

        # 缩放图片
        pixmap = image.scaled(600, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # 如果需要旋转图片
        if self.pic_rotate == 1:
            try:
                self.inst_logger.info("图片开始旋转")
                # 创建 QTransform 对象用于旋转 180 度
                transform = QTransform()
                transform.rotate(180)  # 旋转 180 度

                # 使用 QMatrix 对象来变换 QPixmap
                rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
                pixmap = rotated_pixmap  # 更新 pixmap 为旋转后的图片
            except Exception as e:
                self.inst_logger.info(f"旋转失败: {e}")

        # 在 QPixmap 上绘制条形码
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 设置字体及大小
        font = QFont("Arial", 20)
        painter.setFont(font)
        painter.setPen(Qt.white)  # 设置字体颜色为白色

        # 绘制文本，位置可以根据需求调整
        painter.drawText(220, 50, barcode)  # 在图片的左上角绘制条形码

        # 结束绘制
        painter.end()

        # 获取到对应的 QLabel，并更新显示的图片
        label = frame.layout().itemAt(0).widget()  # 获取到 QLabel
        if label:
            label.setText("")  # 清空原先的文本
            label.setPixmap(pixmap)  # 显示包含条形码文本的图片
        else:
            self.inst_logger.info(f"未找到 {frame_name} 中的 QLabel")

    def init_ui(self):
        # 创建主布局 横线布局
        main_layout = QHBoxLayout()
        # 左侧布局为纵向布局  第一个为图片布局，第二个为信息布局
        leftlayout = QVBoxLayout()
        # 设置字体大小
        font = QtGui.QFont()
        font.setPointSize(20)
        font.setBold(True)
        
        font1 = QtGui.QFont()
        font1.setPointSize(15)
                
        self.setWindowTitle("Manual Scan Client(补码客户端)")
        self.setGeometry(100, 100, 300, 200)

        status_front = QtGui.QFont("Arial",16)
        self.statusbar = QStatusBar()
        self.statusbar.setFont(status_front)
        # self.caps_lock_label = QLabel("Caps Lock : OFF")
        # self.statusbar.addPermanentWidget(self.caps_lock_label)
        #self.pagelabel = QLabel("Current Page : 1")
        #self.statusbar.addWidget(self.pagelabel)

        self.statusbar.showMessage("Client Start",4000)

        self.tpbar = QStatusBar()
        self.tpbar.setFont(status_front)

        self.MAWB = QLabel("MAWB:", self)
        self.MAWB.setFont(font)
        self.mawbid = QLabel("xx", self)
        self.mawbid.setFont(font1)
        self.STATUS = QLabel("Status:", self)
        self.STATUS.setFont(font)
        self.sysstatus = QLabel("status", self)
        self.sysstatus.setFont(font1)
        self.HAWB = QLabel("HAWB:", self)
        self.HAWB.setFont(font)


        # 创建MAWB布局，HAWB布局
        self.MAWBLayout = QHBoxLayout()
        self.MAWBLayout.addWidget(self.MAWB)
        self.MAWBLayout.addWidget(self.mawbid)
        self.MAWBLayout.addWidget(self.STATUS)
        self.MAWBLayout.addWidget(self.sysstatus)
        self.HAWBLayout = QHBoxLayout()
        self.HAWBLayout.addWidget(self.HAWB)
        # 创建HAWBinfo
        self.HAWBinfo = QGridLayout()
        self.HAWBinfocreate()
        # 创建左侧图片布局
        self.pic_layout = QHBoxLayout()
        self.picCreate()

        # 创建左侧皮带机布局
        self.pidaiji_layout = QGridLayout()
        # 设置水平间距
        self.pidaiji_layout.setHorizontalSpacing(0)  # 水平间距为 10 像素

        # 设置垂直间距
        self.pidaiji_layout.setVerticalSpacing(0)  # 垂直间距为 10 像素
        self.pidaijiCreate()
        # 设置皮带机布局的背景图片

        #  设置输入框 和一个提交按钮
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("输入条码")  # 设置输入框的占位符文本
        self.input.setObjectName("edit2")
        # self.input.setFocusPolicy(Qt.NoFocus)
        # 创建提交按钮
        self.btn_submit = QPushButton("提交", self)
        self.btn_submit.setObjectName("submitbutton")
        self.btn_submit.setIcon(QtGui.QIcon("./pic/submit.png"))
        self.btn_submit.setIconSize(QtCore.QSize(28, 28))
        # 隐藏控件
        self.input.hide()
        self.btn_submit.hide()

        # 创建一个网格布局
        self.showdatagridlayout = QGridLayout()
        self.showdatavreate()
        # 添加分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)  # 设置为垂直分割线
        line.setFrameShadow(QFrame.Sunken)  # 设置阴影效果
        # 添加分割线
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)  # 设置为垂直分割线
        line1.setFrameShadow(QFrame.Sunken)  # 设置阴影效果
        # self.btn_submit.setFixedSize(100, 40)  # 设置按钮大小
        # self.btn_submit.clicked.connect(self.submit_clicked)
        leftlayout.addLayout(self.pic_layout, 6)
        leftlayout.addLayout(self.MAWBLayout, 1)
        leftlayout.addWidget(line)
        leftlayout.addLayout(self.HAWBLayout, 1)
        leftlayout.addLayout(self.HAWBinfo, 1)
        leftlayout.addWidget(line1)
        leftlayout.addLayout(self.showdatagridlayout, 1)
        leftlayout.addWidget(self.input, 1)
        leftlayout.addWidget(self.btn_submit, 1)
        leftlayout.addLayout(self.pidaiji_layout, 2)
        leftlayout.addWidget(self.statusbar,1)
        leftlayout.addWidget(self.tpbar,1)
        leftlayout.setContentsMargins(0, 0, 0, 0)

        # 创建右侧布局 table控件
        self.table_layout = QHBoxLayout()
        self.tableCreate()
        # 设置 QTableWidget 的属性，确保它不抢占焦点
        self.tableWidget.setFocusPolicy(Qt.NoFocus)
        # 将左侧布局，table布局加入主布局中

        main_layout.addLayout(leftlayout, 4)
        main_layout.addLayout(self.table_layout, 2)

        # 设置窗口的布局
        self.setLayout(main_layout)

        # 开启线程 循环更新表格内容
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_table)
        self.timer.start(500)
        style_file = './qss/table.qss'
        with open(style_file, 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())
        # 启动一个线程，接收stream数据 并且更新图片
        thread = threading.Thread(target=self.pic_show)
        # 设置线程为守护线程
        thread.daemon = True
        thread.start()
        # 最大化
        # self.showMaximized()
        self.showFullScreen()
        self.setFocus()

    def update_barcode(self, strManualScanBarcode):
        # self.label.setText(f"接收到的条码：{strManualScanBarcode}")
        # 条码存入redis  __cli_id__  manualscan:cli_01:input
        self.inst_redis.setkey(f"manualscan:{self.__prc_name__}:input", f"{strManualScanBarcode}")

    def keyPressEvent(self, event):
        """
        捕捉键盘按键事件，当用户按下键盘时，更新条码内容。
        扫码枪通常会将条码数据当作普通键盘输入，按下回车键表示输入结束。
        """
        key = event.key()
        if key != Qt.Key_Return and key != Qt.Key_Enter:    # 不是回车键
            self.barcode_input += event.text()              # 添加按下的字符到条码输入缓存，返回
            return
        if self.barcode_input == "":
            return
        str_bc_input = str(self.barcode_input)              # 获取str格式的输入信息
        self.barcode_input = ""                             # 清空按键输入缓存
        self.inst_logger.info(f"QT收到的完整输入信息:{str_bc_input}")

        # 判断收到的是条码还是命令，如果不是以*开头，*结尾的，不是命令
        str_command_input = ""
        if str_bc_input.startswith("*") and str_bc_input.endswith("*"):
            str_command_input = str_bc_input[1:-1]
            self.inst_logger.info(f"收到命令: {str_command_input}")
        if str_command_input == "enterclean":   # 进入清场模式
            self.inst_logger.info(f"收到进入清场模式的指令，尝试进入清场模式")
            if self.exception_handling == 1:    # 已经是清场模式
                self.inst_logger.info(f"进入清场模式失败，当前已经在清场模式中")
                return
            str_sys_status = self.inst_redis.getkey("sys:status")
            if str_sys_status != "stop":    # 只允许在系统停止的情况下，进入清场模式
                self.inst_logger.info(f"进入清场模式失败，当前系统在正常运行中")
                return
            # 判断 mr nr ng 三个列表，如果三个列表全部为空，不允许进入清场模式
            set_reading_nr = self.inst_redis.getset("set_reading_nr")  # 更新set_reading_nr
            set_reading_mr = self.inst_redis.getset("set_reading_mr")  # 更新set_reading_mr
            set_reading_gr = self.inst_redis.getset("set_reading_gr")
            set_check_ng =self.inst_redis.getset("set_check_ng")
            if len(set_reading_nr)+ len(set_reading_mr)+len(set_check_ng) == 0:
                self.inst_logger.info(f"进入清场模式失败，NR,MR,NG列表全为空")
                return

            # 开始进入清场模式
            # 向ms 发送清理命令，清理掉所有已扫描的补码信息
            # self.update_barcode(f"*enterclean*")
            self.scanbarcode = ""
            # self.barcode_input = ""  # 清空当前条码

            # 状态值更改
            self.scanned_mr.clear()
            self.scanned_nr.clear()
            self.scanned_mr.clear()
            self.scanned_all.clear()

            self.exception_handling = 1
            self.inst_redis.setkey("sys:status","clean")
            self.inst_logger.info(f"系统进入清场模式")
            self.show_status("⚠ 系统进入清场模式！", "#FFA500")
            return

        if str_command_input == "endclean":     # 离开清场模式
            self.inst_logger.info(f"收到离开清场模式的指令，尝试离开清场模式")
            if self.exception_handling == 0:    # 当前不是清场模式
                self.inst_logger.info(f"离开清场模式失败，当前不在清场模式中")
                return
            # 如果mr数量不匹配
            # 如果nr数量不匹配
            # 如果ng数量不匹配
            # 向ms发送补码结果，间隔1s

            self.inst_redis.clearset("set_reading_nr")
            self.inst_redis.clearset("set_reading_mr")
            self.inst_redis.clearset("set_ms_nr")
            self.inst_redis.clearset("set_ms_mr")
            self.inst_redis.clearset("set_check_ng")
            

            # 状态值更改
            self.exception_handling = 0
            self.inst_redis.setkey("sys:status", "resume") # plc 复位输送机，重启
            self.inst_logger.info(f"系统离开清场模式")
            self.show_status("系统离开清场模式！", "#87CEEB")
            self.exception_list.clear()
            return

        if not str_command_input:       # 收到的是条码
            if self.exception_handling != 1 :       # 正常补码模式，条码发送给ms线程即可
                self.update_barcode(str_bc_input)   # update redis，传递补码信息给ms线程
                self.scanbarcode = str_bc_input     # 传递条码信息给定时更新程序 update_table
                self.show_status(f"✅ 收到条码，{str_bc_input}", "#90EE90")
            else:
                # clean 模式，表格更新、状态显示、声音播放都需要自己处理
                try:
                    # 首先进行条码格式判断
                    bBarcodeValid = False
                    for i, re_exp in enumerate(self.lst_re_exp):  # 遍历所有正则表达式，任何一个通过就说明条码被接受
                        if barcode_formatcheck(str_bc_input, re_exp):  # 如果手动输入的条码通过正则校验,填加至序列等待处理
                            bBarcodeValid = True
                            break
                    if not bBarcodeValid:                       # 不合格条码, 播放声音后退出
                        self.inst_logger.info(f"clean 模式下收到的条码{str_bc_input}不符合格式规范!! ")
                        self.show_status(f"clean 模式：条码 {str_bc_input} 不符合格式规范!!", "#FFB6C1")
                        mixer.music.load(self.dict_sound['ms_barcode_reject'])
                        mixer.music.play()
                        return

                    set_reading_confirm = self.inst_redis.getset("set_reading_confirm")  # 更新set_reading_confirm
                    if str_bc_input in set_reading_confirm:                     # 已确认发出的条码 播放拒绝声音后退出
                        self.inst_logger.info("条码已存在于confirm清单中")
                        self.show_status(f"clean 模式：条码 {str_bc_input} 已回传系统！!", "#FFB6C1")
                        mixer.music.load(self.dict_sound['ms_barcode_exist'])
                        mixer.music.play()
                        return
                    self.exception_list.append(self.barcode_input)              # 排除以上问题，就可将条码加入list,用于变绿

                    set_reading_gr = self.inst_redis.getset("set_reading_gr")   # 排除confirm后的gr 就是CV03上的gr
                    if str_bc_input in set_reading_gr:                          # 扫描正常的包裹
                        self.scanned_all.add(str_bc_input)
                        self.scanned_gr.add(str_bc_input)
                        self.inst_logger.info(f"clean 模式下收到的条码{str_bc_input}在正确读取清单reading_gr中")
                        self.show_status(f"clean 模式：条码 {str_bc_input} 为正确读取条码", "#87CEEB")
                        self.exception_list.append(str_bc_input)    # 用于变绿
                        return

                    set_reading_mr = self.inst_redis.getset("set_reading_mr")  # 匹配多条码 更新set_reading_mr
                    if str_bc_input in set_reading_mr:  # 捕获到多条码
                        self.scanned_mr.add(str_bc_input)
                        mixer.music.load(self.dict_sound['ms_barcode_rescan_accept'])
                        mixer.music.play()
                        self.inst_logger.info(f"clean 模式下收到的条码{str_bc_input}在多条码清单reading_mr中")
                        self.show_status(f"clean 模式：条码 {str_bc_input} 为MR条码", "#87CEEB")
                        return

                    # 收到一个合格条码，但不在以上清单中，视为NR补码
                    self.scanned_nr.add(str_bc_input)
                    mixer.music.load(self.dict_sound['ms_barcode_rescan_accept'])
                    mixer.music.play()
                    self.inst_logger.info(f"clean 模式下收到的条码{str_bc_input}不在任何清单中,视为NR补码成功")
                    self.show_status(f"clean 模式：条码 {str_bc_input} 为NoRead条码", "#87CEEB")
                except Exception as e:
                    print(f"Error in keyPressEvent: {e}")
                    print(traceback.format_exc())

    def tableCreate(self):
        font = QtGui.QFont()
        font.setPointSize(17)
        self.tableWidget = QtWidgets.QTableWidget()
        self.tableWidget.setFont(font)
        self.tableWidget.setAutoScrollMargin(16)
        self.tableWidget.setRowCount(10)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(["条码", "X值", "Y值", "scan","check"])
        self.tableWidget.horizontalHeader().setDefaultSectionSize(258)
        self.tableWidget.setColumnWidth(0, 220)
        self.tableWidget.setColumnWidth(1, 90)
        self.tableWidget.setColumnWidth(2, 90)
        self.tableWidget.setColumnWidth(3, 90)
        self.tableWidget.setColumnWidth(4, 80)
        # self.tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # 左右滚动条
        self.tableWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # 上下滚动条
        self.tableWidget.verticalHeader().setDefaultSectionSize(60)  # 设置行高为50像素（根据需要调整）
        self.tableWidget.horizontalHeader().setMinimumSectionSize(31)
        # 设置整个表格为只读
        self.tableWidget.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table_layout.addWidget(self.tableWidget)

    def picCreate(self):
        for i in range(3):
            frame = QFrame(self)
            frame.setFrameShape(QFrame.StyledPanel)
            # 设置最大宽度
            frame.setMaximumWidth(400)  # 设置框架的最大宽度
            frame.setMaximumHeight(430)  # 设置框架的最大宽度
            # frame.setStyleSheet("background-color: white; border: 1px solid black;")
            label = QLabel(f"图片 {i + 1}", frame)
            label.setAlignment(Qt.AlignCenter)
            frame.setLayout(QVBoxLayout())
            frame.layout().addWidget(label)
            self.pic_layout.addWidget(frame)  # 第一行添加三个框
            # 给每个框设置唯一的对象名
            if self.pic_direction == 1:
                frame.setObjectName(f"frame_{2 - i}")
            else:
                frame.setObjectName(f"frame_{i}")

    def pidaijiCreate(self):
        # 初始化计数器
        counter = 0

        # 根据是否镜像来决定如何设置名字
        if self.is_image == 0:
            # 不是镜像，从左往右设置名字
            for i in range(3):
                for j in range(6):
                    frame = QFrame(self)
                    frame.setFrameShape(QFrame.StyledPanel)
                    frame.setMaximumWidth(300)
                    frame.setMaximumHeight(50)
                    frame.setStyleSheet("background-color: grey; border: 1px solid black;")
                    self.pidaiji_layout.addWidget(frame, i, j)
                    frame.setObjectName(str(counter))
                    counter += 1
        else:
            # 是镜像，从右往左设置名字
            for i in range(3):
                for j in range(6):
                    frame = QFrame(self)
                    frame.setFrameShape(QFrame.StyledPanel)
                    frame.setMaximumWidth(300)
                    frame.setMaximumHeight(100)
                    frame.setStyleSheet("background-color: grey; border: 0px solid black;")
                    self.pidaiji_layout.addWidget(frame, i, 5 - j)  # 从右往左添加
                    frame.setObjectName(str(counter))
                    counter += 1
        if self.level == 0:
            self.y1 = int(0)
            self.y2 = int(400)
            self.y3 = int(400)
            self.y4 = int(800)
            self.y5 = int(800)
            self.y6 = int(1200)
        else:
            self.y1 = int(800)
            self.y2 = int(1200)
            self.y3 = int(400)
            self.y4 = int(800)
            self.y5 = int(0)
            self.y6 = int(400)

    def update_table(self):
        try:
            # 如command区收到退出命令，根据线程类型决定是否立即退出
            prc_run_lock = self.inst_redis.getkey(f"sys:cli{self.__cli_id__:02}:command")
            if prc_run_lock == "exit":
                # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
                # 如有则暂缓退出，如没有立即退出
                self.close()
                int_exit_code = 2
                return
            # 获取redis中plc是否停线，如果plc停线，进入异常处理操作
            self.control_update()

            # plc_conv_status = self.inst_redis.getkey("sys:status")
            # 扫描特殊条码*clean* 进入手动清场这模式
            # if plc_conv_status == 'clean' and self.exception_handling == 0:
            #    time.sleep(1)
            #    if self.inst_redis.getkey("plc_conv:status") == 'pause':
            #        self.exception_handling = 1
                    # 创建一个消息框
            #        msg_box = QMessageBox()
            #        msg_box.setIcon(QMessageBox.Critical)
            #        msg_box.setText("请逐个扫描包裹条码")
            #        msg_box.setWindowTitle("！！进入清场模式！！")
            #        msg_box.setStandardButtons(QMessageBox.Ok)  #后续改成不显示cancel 不能直接按回车取消 避免直接扫描条码的回车带走该框
            #        msg_box.exec_()

            # 先将所有颜色恢复成灰色
            for i in range(18):
                frame = self.findChild(QFrame, str(i))
                if frame:
                    # 应用样式表设置颜色
                    frame.setStyleSheet(f"background-color: 'grey';")

            self.tableWidget.clearContents()
            # 获取所有匹配的 parcel:scan_result:* 键
            # keys = self.inst_redis.keys('parcel:scan_result:*')
            # keys = self.inst_redis.getbuff('parcel:scan_result:*')
            # 存储结果的列表
            self.results = []
            # print(keys)
            # 使用副本进行迭代
            for key in list(self.uid_deque):  # 将 deque 转换为 list
                # 解码键名
                key_str = key
                # 从键名中提取出 'xxx' 部分
                if key_str == None:
                    return
                B_id = key
                # 构建对应的 posx, posy, scan_result 键
                barcode_key = f"parcel:barcode:{B_id}"
                posx_key = f"parcel:posx:{B_id}"
                posy_key = f"parcel:posy:{B_id}"
                scan_result_key = f"parcel:scan_result:{B_id}"
                check_result_key = f"parcel:check_result:{B_id}"
                # 获取对应的值
                barcode_value = self.inst_redis.getkey(barcode_key)
                posx_value = self.inst_redis.getkey(posx_key)
                posy_value = self.inst_redis.getkey(posy_key)
                scan_result_value = self.inst_redis.getkey(scan_result_key)
                check_result_value = self.inst_redis.getkey(check_result_key)
                if barcode_value == None and posx_value == None and posy_value == None and scan_result_value == None:
                    if key in self.uid_deque:
                        self.uid_deque.remove(key)
                    continue
                # 将值放入列表中
                self.results.append({
                    'barcode': barcode_value,
                    'posx': posx_value,
                    'posy': posy_value,
                    'scan_result': scan_result_value,
                    'check_result': check_result_value
                })

                #
                # 更新表格
                # self.tableWidget.setRowCount(len(results))  # 设置行数
            for row, result in enumerate(self.results):
                self.tableWidget.setItem(row, 0, QTableWidgetItem(result['barcode']))
                self.tableWidget.setItem(row, 1, QTableWidgetItem(result['posx']))
                self.tableWidget.setItem(row, 2, QTableWidgetItem(result['posy']))
                self.tableWidget.setItem(row, 3, QTableWidgetItem(result['scan_result']))
                self.tableWidget.setItem(row, 4, QTableWidgetItem(result['check_result']))
                # 如果补码的值与barcode一样  将table变色
                try:
                    if result['barcode'] == self.scanbarcode:
                        item = self.tableWidget.item(row, 0)
                        item.setBackground(QBrush(QColor(255, 105, 180)))  # 背景颜色
                    if result['barcode'] in self.exception_list:
                        item = self.tableWidget.item(row, 0)
                        item.setBackground(QBrush(QColor(59, 241, 146)))
                except Exception as e:
                    # self.inst_logger(f"{keys}")
                    self.inst_logger.info(f"{result['barcode']}为空")

                scan_result = "green"
                # 将包裹位置更新 判断包裹xy 具体什么包裹变色
                if result['scan_result'] == 'GR':
                    scan_result = "green"
                elif result['scan_result'] == 'NR':
                    scan_result = "red"
                elif result['scan_result'] == 'MR':
                    scan_result = "yellow"
                if result['posx'] is None or result['posy'] is None:
                    self.inst_logger.info(f"barcode={result['barcode']}:posx={result['posx']},posy={result['posy']}")
                    continue
                posx_value1 = int(result['posx'])
                posy_value1 = int(result['posy'])
                # print(f"posx={posx_value},posy={posy_value}")
                if self.y1 <= posy_value1 < self.y2:
                    if 1700 <= posx_value1 < 2266:
                        self.updateColor(0, scan_result, result['barcode'])
                    if 2266 <= posx_value1 < 2832:
                        self.updateColor(1, scan_result, result['barcode'])
                    if 2832 <= posx_value1 < 3398:
                        self.updateColor(2, scan_result, result['barcode'])
                    if 3398 <= posx_value1 < 3964:
                        self.updateColor(3, scan_result, result['barcode'])
                    if 3964 <= posx_value1 < 4530:
                        self.updateColor(4, scan_result, result['barcode'])
                    if 4530 <= posx_value1 < 5100:
                        self.updateColor(5, scan_result, result['barcode'])
                # 第二列
                if self.y3 <= posy_value1 < self.y4:
                    if 1700 <= posx_value1 < 2266:
                        self.updateColor(6, scan_result, result['barcode'])
                    if 2266 <= posx_value1 < 2832:
                        self.updateColor(7, scan_result, result['barcode'])
                    if 2832 <= posx_value1 < 3398:
                        self.updateColor(8, scan_result, result['barcode'])
                    if 3398 <= posx_value1 < 3964:
                        self.updateColor(9, scan_result, result['barcode'])
                    if 3964 <= posx_value1 < 4530:
                        self.updateColor(10, scan_result, result['barcode'])
                    if 4530 <= posx_value1 < 5100:
                        # print(1232323232)
                        self.updateColor(11, scan_result, result['barcode'])
                # 第三列
                if self.y5 <= posy_value1 < self.y6:
                    if 1700 <= posx_value1 < 2266:
                        self.updateColor(12, scan_result, result['barcode'])
                    if 2266 <= posx_value1 < 2832:
                        self.updateColor(13, scan_result, result['barcode'])
                    if 2832 <= posx_value1 < 3398:
                        self.updateColor(14, scan_result, result['barcode'])
                    if 3398 <= posx_value1 < 3964:
                        self.updateColor(15, scan_result, result['barcode'])
                    if 3964 <= posx_value1 < 4530:
                        self.updateColor(16, scan_result, result['barcode'])
                    if 4530 <= posx_value1 < 5100:
                        self.updateColor(17, scan_result, result['barcode'])

        except Exception as e:
            print(f"Error in update_table: {e}")
            # self.inst_logger(f"{keys}")
            self.inst_logger.error(f"线程{self.__prc_name__}发生错误,错误为{traceback.format_exc()}")
            print(traceback.format_exc())

    # def submit_clicked(self):
    #     try:
    #         current_barcode = '##' + self.input.text()
    #         self.inst_logger.info(f"手动提交的条码：{current_barcode}")
    #         self.input.setText('')
    #         self.update_barcode(current_barcode)
    #         self.setFocus()
    #     except Exception as e:
    #         print(traceback.format_exc())

    def updateColor(self, name, result, barcode_value):
        # print(name, result)
        # 检查是否为绿色  如果是绿色 不覆盖 直接跳过

        name = str(name)
        frame = self.findChild(QFrame, name)
        if frame:
            # 应用样式表设置颜色
            frame.setStyleSheet(f"background-color: {result};")

    def pic_show(self):
        self.image_list = []
        self.max_length = 4  # 最大图片数为4
        # 用双端队列存储 UID
        while True:
            # 模拟线程执行任务
            # 当获取到有数据流后，将条码贴到图片上 再将图片上 显示图片先显示图片1 如果又有图片来后 将图片1移动到图片2， 图片2移动到图片3
            try:
                stream_test = self.inst_redis.xreadgroup(self.stream_name_create, self.__prc_name__, "consumer1")
                stream_reading_confirm = self.inst_redis.xreadgroup(self.stream_name_delete, self.__prc_name__,
                                                                    "consumer1")
                try:
                    if stream_test:
                        self.inst_logger.info(
                            "stream_test收到序列 %s 中的消息累计 %d 行" % (stream_test[0][0], len(stream_test[0][1])))
                        for i, dictdata in stream_test[0][1]:  # 遍历收到的所有消息
                            uid = dictdata['uid']  # 正常识读
                            result = dictdata['result']
                            code = dictdata['code']
                            self.inst_logger.info(f"获取到UID:{uid},result={result},code={code}")
                            if uid is None or result is None:
                                continue
                            # 添加uid到队列中
                            self.uid_deque.append(uid)

                            # 先找到图片
                            # 查找包含uid的图片
                            if result == 'GR':
                                # 全部显示功能开关
                                if not self.all_show_flag:  # 如果皮带机不处于正常，就不显示GR
                                    continue
                                plc_status = self.inst_redis.getkey('plc_conv:fullspeed')
                                if plc_status != 'yes':
                                    continue
                                path = self.AITarget_file_path
                                ftp_path = self.ftp_path_Alread
                            elif result == 'NR':
                                path = self.NoTarget_path
                                ftp_path = self.ftp_path_Noread
                                code = 'NoRead'
                            elif result == 'MR':
                                uid = uid[:-2]
                                path = self.ErrTarget_path
                                ftp_path = self.ftp_path_Errread
                                code = 'MrRead'
                            # 用uid去指定文件夹下获取对应的图片
                            # 先构建 图片路径 获取当前日期
                            now = datetime.datetime.now()
                            day = now.strftime("%Y-%m-%d")

                            path = path + '\\' + day + '\\'
                            ftp_path = ftp_path + '/' + day + '/'
                            print(path)
                            print(ftp_path)
                            # 先从ftp上下载图片####
                            self.ftp_download(path, uid, ftp_path)
                            ##### 将上一次的图片路径取消掉
                            full_path = ''
                            if os.path.exists(path):
                                # 遍历目录中的所有文件
                                for filename in os.listdir(path):
                                    if uid in filename:  # 如果文件名中包含uid
                                        full_path = os.path.join(path, filename)
                                        print(f"图片路径为{full_path}")
                            # self.image_list.append([uid, code, result, full_path])
                            if full_path == '':
                                self.inst_logger.info(f"本机图片为空，使用默认图片展示")
                                full_path = 'C:\\TEST\\Image\\RGBDPano\\default.jpg'
                            self.image_list.insert(0, [uid, code, result, full_path])
                            # 如果列表长度达到最大值，删除最旧的图片
                            if len(self.image_list) >= self.max_length:
                                self.image_list.pop()  # 删除最后一个元素
                            for ant in range(len(self.image_list)):
                                self.addImageToFrame(f"frame_{ant}", self.image_list[ant][3], self.image_list[ant][1])
                except Exception as e:
                    self.inst_logger.error("图片获取失败")
                    self.inst_logger.error(f"{traceback.format_exc()}")
                try:
                    if stream_reading_confirm:
                        self.inst_logger.info("收到序列 %s 中的消息累计 %d 行" % (stream_reading_confirm[0][0],
                                                                       len(stream_reading_confirm[0][1])))
                        for i, dictdata in stream_reading_confirm[0][1]:  # 遍历收到的所有消息
                            uid = dictdata['uid']  # 正常识读
                            self.inst_logger.info(f"stream_reading_confirm获取到UID:{uid}")
                            if uid is None:
                                continue
                            # 从队列中删除uid
                            if uid in self.uid_deque:
                                self.uid_deque.remove(uid)  # 从 deque 中删除该 UID
                            else:
                                self.inst_logger.error(f"{uid}不在队列中，无法删除")
                except Exception as e:
                    self.inst_logger.error("stream_reading_confirm删除队列失败")
                    self.inst_logger.error(f"{traceback.format_exc()}")
            except Exception as e:
                self.inst_logger.error("出现错误")
                time.sleep(5)
                self.inst_logger.error(f"{traceback.format_exc()}")

    def ftp_download(self, path, uid, ftp_path):
        count = 0
        for i in range(5):
            time.sleep(0.5)
            # 连接到FTP服务器
            ip = self.server_ip
            ftp = FTP(ip)  # 服务器地址
            ftp.login('ftp', '')  # 使用正确的用户名和密码
            self.inst_logger.info(f"ftp_path{ftp_path}")
            # 图片文件的路径，切换到正确的目录
            ftp.cwd(f'{ftp_path}')  # 实际路径
            # 列出目录中的所有文件，找到匹配的文件
            file_list = ftp.nlst()  # 获取当前目录下的所有文件名
            # self.inst_logger.info(f"当前图片文件列表为{file_list}")
            # 根据uid查找相关文件
            find_pic = None

            for filename in file_list:
                if str(uid) in filename:  # 假设文件名中包含uid
                    find_pic = filename
                    break
            # 下载图片
            if find_pic is None:
                self.inst_logger.info(f"第{i}次未找到图片 {find_pic}")
                ftp.quit()
                continue
            else:
                self.inst_logger.info(f"开始下载图片 {find_pic}")
                local_path = f'{path}{find_pic}'  # 本地保存路径
                # 检查路径是否存在 不存在则创建路径
                if not os.path.exists(path):
                    os.makedirs(path)
                self.inst_logger.info(f"图片下载地址 {local_path}")
                with open(local_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {find_pic}', f.write)  # 替换为实际的图片文件名
                # 关闭FTP连接
                ftp.quit()
                break

    def barcode_formatcheck(self, str_barcode, re_exp):
        """
        条码校验
        """
        res = re.search(re_exp, str_barcode)
        print(" checking re_exp=%s,barcode=%s,result = %s" % (re_exp, str_barcode, res))
        if res:
            return True
        else:
            return False

    def get_parcel_uid(self, barcode_type):
        """
        通过NR MR 获取对应的uid
        barcode_type : NR MR GR
        """
        keys = self.inst_redis.keys('parcel:scan_result:*')
        print(keys)
        nr_keys = []  # 用于存储找到的 NR 键
        for key in keys:
            # 解码键名
            parts = key.split(':')  # 分割键名
            if len(parts) == 3 and parts[0] == 'parcel' and parts[1] == 'scan_result':
                scan_result_key = key  # 完整的键名
                scan_result_value = self.inst_redis.getkey(scan_result_key)  # 获取键的值

                if scan_result_value == barcode_type:  # 检查值是否为 barcode_type
                    # 提取 ** 部分
                    xxx = parts[2]
                    nr_keys.append(xxx)  # 将 ** 部分存起来
        # 返回找到的NR键的uid
        self.inst_logger.info("找到的 %s 键对应的 uid 部分: %s", barcode_type, nr_keys)
        return nr_keys

    def clear_parcel_uid(self, uid):
        """
        通过uid清空parcel中对应的内容
        """
        self.inst_redis.clearkey(f'parcel:scan_result:{uid}')
        self.inst_redis.clearkey(f'parcel:barcode:{uid}')
        self.inst_redis.clearkey(f'parcel:posx:{uid}')
        self.inst_redis.clearkey(f'parcel:posy:{uid}')
        self.inst_redis.clearkey(f'parcel:sid:{uid}')

    def recovery_PLC_Speed(self):
        self.inst_redis.setkey("plc_conv:command", 'start')  # 重新启动
        self.inst_logger.info("人工处理操作成功，线程 %s 尝试重新启动输送机" % (self.__prc_name__,))
        self.exception_handling = 0
        self.inst_logger.info("清除异常状态位exception_handling = 0")
        self.exception_list = []
        self.nofound_list = []
        self.inst_logger.info("清除扫入条码列表和未出现的列表")
        # self.label1.setText("未出现过的条码：")
        self.barcode_input = ""  # 清空当前条码

    def control_update(self):
        lst_reading_nr = list(self.inst_redis.getset("set_reading_nr"))  # 更新set_reading_nr
        set_reading_mr = self.inst_redis.getset("set_reading_mr")  # 更新set_reading_mr
        str_sysstatus = self.inst_redis.getkey("sys:status")  # 更新sys status
        if str_sysstatus == "normal":
            str_tp_short = self.inst_redis.getkey("tp:short")
            str_tp_long = self.inst_redis.getkey("tp:long")
            if str_tp_long:
                self.tpbar.showMessage(f"流量已更新，瞬时流量 {str_tp_short} 件/小时；平均流量 {str_tp_long} 件/小时")
        set_hawb = self.inst_redis.getset("set_hawb") # 更新运单数据    
        self.NR.setText(f"NR:{len(lst_reading_nr)}")
        self.MR.setText(f"MR:{len(set_reading_mr)}")

        self.sysstatus.setText(f"{str_sysstatus}")
        self.total_number.setText(f"{len(set_hawb)}")

        str_batchid = self.inst_redis.getkey("sys:batchid")
        self.mawbid.setText(str_batchid)

        str_batchid_count = self.inst_redis.getkey("sys:hawb:count")
        self.hpk_number.setText(str_batchid_count)
        self.out_number.setText("0")
        if len(lst_reading_nr) == 0:
            self.NR_1.setText(f"")
            self.NR_2.setText(f"")
            self.NR_3.setText(f"")

        for i in range(len(lst_reading_nr)):
            if i == 0:
                self.NR_1.setText(f"NO READ BARCODE")
                self.NR_2.setText(f"")
                self.NR_3.setText(f"")
                continue
            if i == 1:
                self.NR_1.setText(f"NO READ BARCODE")
                self.NR_2.setText(f"NO READ BARCODE")
                self.NR_3.setText(f"")
                continue
            if i >= 2:
                self.NR_1.setText(f"NO READ BARCODE")
                self.NR_2.setText(f"NO READ BARCODE")
                self.NR_3.setText(f"NO READ BARCODE")
                continue
        templst_reading_mr = list(set_reading_mr)  # 将集合转换为列表
        if len(set_reading_mr) == 0:
            self.MR_1.setText(f"")
            self.MR_2.setText(f"")
            self.MR_3.setText(f"")

        for i in range(len(set_reading_mr)):
            if i == 0:
                self.MR_1.setText(f"{templst_reading_mr[0]}")
                continue
            if i == 1:
                self.MR_2.setText(f"{templst_reading_mr[1]}")
                continue
            if i >= 2:
                self.MR_3.setText(f"{templst_reading_mr[2]}")
                continue

    def showdatavreate(self):
        # 创建网格布局
        # 创建控件
        font = QtGui.QFont()
        font.setPointSize(20)
        font.setBold(True)
        font1 = QtGui.QFont()
        font1.setPointSize(15)
        palette = QPalette()
        self.NR = QLabel("NR:")
        # 创建调色板对象

        # 设置背景颜色为你需要的颜色（例如，红色）
        # palette.setColor(QPalette.Background, QColor(255, 0, 0))  # 红色
        # self.NR.setAutoFillBackground(True)  # 使背景填充生效
        # 应用调色板
        # self.NR.setPalette(palette)
        self.MR = QLabel("MR:")
        # self.MR.setAutoFillBackground(True)  # 使背景填充生效
        # 应用调色板
        # self.MR.setPalette(palette)
        self.NG = QLabel("NG:")
        # 设置文本居中
        self.NR.setAlignment(Qt.AlignCenter)
        self.MR.setAlignment(Qt.AlignCenter)
        self.NG.setAlignment(Qt.AlignCenter)


        self.NR_1 = QLabel("xx")
        self.NR_2 = QLabel("xx")
        self.NR_3 = QLabel("xx")
        self.MR_1 = QLabel("xx")
        self.MR_2 = QLabel("xx")
        self.MR_3 = QLabel("xx")
        self.NG_1 = QLabel("xx")
        self.NG_2 = QLabel("xx")
        self.NG_3 = QLabel("xx")

        self.NR_1.setAlignment(Qt.AlignCenter)
        self.NR_2.setAlignment(Qt.AlignCenter)
        self.NR_3.setAlignment(Qt.AlignCenter)
        self.MR_1.setAlignment(Qt.AlignCenter)
        self.MR_2.setAlignment(Qt.AlignCenter)
        self.MR_3.setAlignment(Qt.AlignCenter)
        self.NG_1.setAlignment(Qt.AlignCenter)
        self.NG_2.setAlignment(Qt.AlignCenter)
        self.NG_3.setAlignment(Qt.AlignCenter)

        self.NR.setFont(font)
        self.MR.setFont(font)
        self.NG.setFont(font)
        self.NR_1.setFont(font1)
        self.NR_2.setFont(font1)
        self.NR_3.setFont(font1)
        self.MR_1.setFont(font1)
        self.MR_2.setFont(font1)
        self.MR_3.setFont(font1)
        self.NG_1.setFont(font1)
        self.NG_2.setFont(font1)
        self.NG_3.setFont(font1)

        # 将控件添加到布局中，指定控件的行列位置
        self.showdatagridlayout.addWidget(self.NR, 0, 0)  # 行0列0
        self.showdatagridlayout.addWidget(self.MR, 0, 1)  # 行0列1
        self.showdatagridlayout.addWidget(self.NG, 0, 2)  # 行0列2
        self.showdatagridlayout.addWidget(self.NR_1, 1, 0)  # 行1列0
        self.showdatagridlayout.addWidget(self.NR_2, 2, 0)  # 行2列0
        self.showdatagridlayout.addWidget(self.NR_3, 3, 0)  # 行3列1
        self.showdatagridlayout.addWidget(self.MR_1, 1, 1)  # 行1列0
        self.showdatagridlayout.addWidget(self.MR_2, 2, 1)  # 行2列0
        self.showdatagridlayout.addWidget(self.MR_3, 3, 1)  # 行3列1
        self.showdatagridlayout.addWidget(self.NG_1, 1, 2)  # 行1列0
        self.showdatagridlayout.addWidget(self.NG_2, 2, 2)  # 行2列0
        self.showdatagridlayout.addWidget(self.NG_3, 3, 2)  # 行3列1

    def HAWBinfocreate(self):
        font = QtGui.QFont()
        font.setPointSize(20)
        font1 = QtGui.QFont()
        font1.setPointSize(15)
        font.setBold(True)
        self.total = QLabel("Total")
        self.hpk = QLabel("HPK")
        self.out = QLabel("OUT")
        self.total_number = QLabel("143")
        self.hpk_number = QLabel("xxx")
        self.out_number = QLabel("xxx")
        self.total.setFont(font)
        self.hpk.setFont(font)
        self.out.setFont(font)
        self.total_number.setFont(font1)
        self.hpk_number.setFont(font1)
        self.out_number.setFont(font1)
        # 设置文本居中
        self.total.setAlignment(Qt.AlignCenter)
        self.hpk.setAlignment(Qt.AlignCenter)
        self.out.setAlignment(Qt.AlignCenter)
        self.total_number.setAlignment(Qt.AlignCenter)
        self.hpk_number.setAlignment(Qt.AlignCenter)
        self.out_number.setAlignment(Qt.AlignCenter)

        self.HAWBinfo.addWidget(self.total, 0, 0)
        self.HAWBinfo.addWidget(self.hpk, 0, 1)
        self.HAWBinfo.addWidget(self.out, 0, 2)
        self.HAWBinfo.addWidget(self.total_number, 1, 0)
        self.HAWBinfo.addWidget(self.hpk_number, 1, 1)
        self.HAWBinfo.addWidget(self.out_number, 1, 2)
    # 添加分割线
    #     line = QFrame()
    #     line.setFrameShape(QFrame.HLine)  # 设置为水平分割线
    #     line.setFrameShadow(QFrame.Sunken)  # 设置分割线的阴影效果
    #     self.HAWBinfo.addWidget(line, 2, 0, 1, 3)  # 这个方法会让分割线跨越 0 到 2 列
    def show_status(self, message, color):
        self.statusbar.showMessage(message)
        self.statusbar.setStyleSheet(f"background: {color};")
        # QTimer.singleShot(2000, self.clear_status)

def start_process(config_file, __cli_id__):
    __prc_cli_type__ = f"cli_qt"
    __prc_name__ = f"cli%02d_qt" % (__cli_id__,)
    print(f"线程 {__prc_name__} 正在启动")

    ini_config = clsConfig(config_file)  # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)
    inst_redis = clsRedis(ini_config)
    inst_logger.info("线程 %s 正在启动" % (__prc_name__,))

    # cli 使用 Redis Ex,各自使用独立实例,每次初始化后都需要重连
    inst_redis.connect(ini_config)
    inst_logger.info("线程 %s Redis 连接成功" % (__prc_name__,))

    # 本地ini文件存储的本线程专有配置参数
    # 定义线程循环时间、过期时间、健康时间等
    str_ini_file_name = "main_%s.ini" % (__prc_cli_type__,)
    __ini_prc_config__ = clsConfigEx(str_ini_file_name)

    inst_logger.info("线程 %s 取得cli_id = %d" % (__prc_name__, __cli_id__))

    # 记录线程启动时间
    __prc_start_ts__ = datetime.datetime.now()
    inst_redis.setkey(f"pro_mon:{__prc_name__}:start_ts", __prc_start_ts__.isoformat())
    inst_logger.info("线程 %s 启动时间 start_ts= %s" % (__prc_name__, __prc_start_ts__.isoformat()))

    inst_logger.info("cli_manualscan start")
    # 创建条码显示窗口
    app = QApplication(sys.argv)
    barcode_display = BarcodeDisplay(inst_redis, __cli_id__, inst_logger, __prc_name__, __ini_prc_config__)
    barcode_display.show()
    sys.exit(app.exec_())


def addImageToFrame(self, frame_name, i, barcode):
    # 使用对象名找到相应的 QFrame

    image = QPixmap(f"{i}")  # i 是图片的路径
    pixmap = image.scaled(600, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # 在 QPixmap 上绘制条形码
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    # 设置字体及大小
    font = QFont("Arial", 20)
    painter.setFont(font)
    painter.setPen(Qt.white)  # 设置字体颜色为白色

    # 绘制文本，位置可以根据需求调整
    painter.drawText(220, 50, barcode)  # 在图片的左上角绘制条形码

    # 结束绘制
    painter.end()

    # 获取到对应的 QFrame，并更新 QLabel 显示的图片
    frame = self.findChild(QFrame, frame_name)
    if frame:
        label = frame.layout().itemAt(0).widget()  # 获取到 QLabel
        label.setText("")  # 清空原先的文本
        label.setPixmap(pixmap)  # 显示包含条形码文本的图片
