# prc_template  v 0.2.0
import sys
import threading
import time
import datetime
import traceback

import pygame
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication, QFrame, QLabel, QVBoxLayout, QSplitter, QHBoxLayout, \
    QTableWidgetItem, QLineEdit, QPushButton

from fBarcode import barcode_formatcheck
from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis
from pygame import mixer


class BarcodeDisplay(QWidget):
    try:
        def __init__(self, inst_redis, __cli_id__, inst_logger, __prc_name__, __ini_prc_config__):
            super().__init__()
            self.inst_redis = inst_redis
            self.__cli_id__ = __cli_id__
            self.inst_logger = inst_logger
            self.__prc_name__ = __prc_name__
            self.is_image = __ini_prc_config__.qt.image
            self.level = __ini_prc_config__.qt.level
            self.barcode_input = ""  # 用来存储接收到的条码
            self.init_ui()

        def init_ui(self):
            # 创建主布局 横线布局
            main_layout = QHBoxLayout()
            # 左侧布局为纵向布局  第一个为图片布局，第二个为信息布局
            leftlayout = QVBoxLayout()
            # 设置字体大小
            font = QtGui.QFont()
            # 设置字体大小
            font.setPointSize(20)  # 设置字体大小为 20
            self.setWindowTitle("接收条码")
            self.setGeometry(100, 100, 300, 200)

            self.label = QLabel("接收到的条码：", self)

            self.label.setFont(font)

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
            # self.btn_submit.setFixedSize(100, 40)  # 设置按钮大小
            self.btn_submit.clicked.connect(self.submit_clicked)

            leftlayout.addWidget(self.label, 3)  # 设置比例
            leftlayout.addWidget(self.input, 1)
            leftlayout.addWidget(self.btn_submit, 1)
            leftlayout.addLayout(self.pidaiji_layout, 2)

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
            # 最大化
            self.showMaximized()
            self.setFocus()

        def update_barcode(self, strManualScanBarcode):
            self.label.setText(f"接收到的条码：{strManualScanBarcode}")
            # 条码存入redis  __cli_id__  manualscan:cli_01:input
            self.inst_redis.setkey(f"manualscan:{self.__prc_name__}:input", f"{strManualScanBarcode}")

        def keyPressEvent(self, event):
            """
            捕捉键盘按键事件，当用户按下键盘时，更新条码内容。
            扫码枪通常会将条码数据当作普通键盘输入，按下回车键表示输入结束。
            """
            try:
                key = event.key()

                if key == Qt.Key_Return or key == Qt.Key_Enter:
                    # print(self.barcode_input)
                    # 回车键表示条码输入完成
                    if self.barcode_input:
                        self.update_barcode(self.barcode_input)
                        self.barcode_input = ""  # 清空当前条码
                else:
                    # 添加按下的字符到条码输入
                    self.barcode_input += event.text()

                # # 更新显示的条码
                # self.update_barcode(self.barcode_input)

            except Exception as e:
                print(f"Error in keyPressEvent: {e}")
                print(traceback.format_exc())
    except:
        print(traceback.format_exc())

    def tableCreate(self):
        font = QtGui.QFont()
        font.setPointSize(17)
        self.tableWidget = QtWidgets.QTableWidget()
        self.tableWidget.setFont(font)
        self.tableWidget.setAutoScrollMargin(16)
        self.tableWidget.setRowCount(20)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setHorizontalHeaderLabels(["条码", "X值", "Y值", "状态"])
        self.tableWidget.horizontalHeader().setDefaultSectionSize(258)
        self.tableWidget.setColumnWidth(0, 270)
        self.tableWidget.setColumnWidth(1, 100)
        self.tableWidget.setColumnWidth(2, 100)
        self.tableWidget.setColumnWidth(3, 100)
        # self.tableWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 左右滚动条
        self.tableWidget.verticalHeader().setDefaultSectionSize(100)  # 设置行高为50像素（根据需要调整）
        self.tableWidget.horizontalHeader().setMinimumSectionSize(31)
        # 设置整个表格为只读
        self.tableWidget.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table_layout.addWidget(self.tableWidget)

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

                    frame.setMaximumHeight(100)
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
            #如command区收到退出命令，根据线程类型决定是否立即退出
            prc_run_lock=self.inst_redis.getkey(f"sys:cli{self.__cli_id__:02}:command")
            if prc_run_lock == "exit":
                # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
                # 如有则暂缓退出，如没有立即退出
                self.close()
                int_exit_code = 2           
                return            
            
            # 先将所有颜色恢复成灰色
            for i in range(18):
                frame = self.findChild(QFrame, str(i))
                if frame:
                    # 应用样式表设置颜色
                    frame.setStyleSheet(f"background-color: 'grey';")

            self.tableWidget.clearContents()
            # 获取所有匹配的 parcel:scan_result:* 键
            keys = self.inst_redis.keys('parcel:scan_result:*')
            # keys = self.inst_redis.getbuff('parcel:scan_result:*')
            # print(keys)
            # 存储结果的列表
            results = []
            # print(keys)
            for key in keys:
                # 解码键名
                key_str = key

                # 从键名中提取出 'xxx' 部分
                if key_str == None:
                    return
                parts = key_str.split(':')
                if len(parts) == 3 and parts[0] == 'parcel' and parts[1] == 'scan_result':

                    B_id = parts[2]
                    # 构建对应的 posx, posy, scan_result 键
                    barcode_key = f"parcel:barcode:{B_id}"
                    posx_key = f"parcel:posx:{B_id}"
                    posy_key = f"parcel:posy:{B_id}"
                    scan_result_key = f"parcel:scan_result:{B_id}"

                    # 获取对应的值
                    barcode_value = self.inst_redis.getkey(barcode_key)
                    posx_value = self.inst_redis.getkey(posx_key)
                    posy_value = self.inst_redis.getkey(posy_key)
                    scan_result_value = self.inst_redis.getkey(scan_result_key)

                    # 将值放入列表中
                    results.append({
                        'barcode': barcode_value,
                        'posx': posx_value,
                        'posy': posy_value,
                        'scan_result': scan_result_value
                    })

                #
                # 更新表格
                # self.tableWidget.setRowCount(len(results))  # 设置行数
                for row, result in enumerate(results):
                    self.tableWidget.setItem(row, 0, QTableWidgetItem(result['barcode']))
                    self.tableWidget.setItem(row, 1, QTableWidgetItem(result['posx']))
                    self.tableWidget.setItem(row, 2, QTableWidgetItem(result['posy']))
                    self.tableWidget.setItem(row, 3, QTableWidgetItem(result['scan_result']))
                    scan_result = "black"
                    # 将包裹位置更新 判断包裹xy 具体什么包裹变色

                    if scan_result_value == 'GR':
                        scan_result = "green"
                    elif scan_result_value == 'NR':
                        scan_result = "red"
                    elif scan_result_value == 'MR':
                        scan_result = "blue"
                    # 设置背景颜色为scan_result

                    # 创建一个新的 QTableWidgetItem 对象，并设置其背景色
                    # item = QTableWidgetItem(result['scan_result'])  # 保留原来的文本
                    # #print(scan_result)
                    # item.setBackground(QColor(scan_result))  # 设置背景颜色
                    # 更新表格中的单元格
                    # self.tableWidget.setItem(row, 3, item)
                    # 第一列
                    # if posx_value == None or posy_value == None:
                    #     continue

                    posx_value1 = int(posx_value)
                    posy_value1 = int(posy_value)
                    if self.y1 <= posy_value1 < self.y2:
                        if 1700 <= posx_value1 < 2266:
                            self.updateColor(0, scan_result)
                        if 2266 <= posx_value1 < 2832:
                            self.updateColor(1, scan_result)
                        if 2832 <= posx_value1 < 3398:
                            self.updateColor(2, scan_result)
                        if 3398 <= posx_value1 < 3964:
                            self.updateColor(3, scan_result)
                        if 3964 <= posx_value1 < 4530:
                            self.updateColor(4, scan_result)
                        if 4530 <= posx_value1 < 5100:
                            self.updateColor(5, scan_result)
                    # 第二列
                    if self.y3 <= posy_value1 < self.y4:
                        if 1700 <= posx_value1 < 2266:
                            self.updateColor(6, scan_result)
                        if 2266 <= posx_value1 < 2832:
                            self.updateColor(7, scan_result)
                        if 2832 <= posx_value1 < 3398:
                            self.updateColor(8, scan_result)
                        if 3398 <= posx_value1 < 3964:
                            self.updateColor(9, scan_result)
                        if 3964 <= posx_value1 < 4530:
                            self.updateColor(10, scan_result)
                        if 4530 <= posx_value1 < 5100:
                            self.updateColor(11, scan_result)
                    # 第三列
                    if self.y5 <= posy_value1 < self.y6:
                        if 1700 <= posx_value1 < 2266:
                            self.updateColor(12, scan_result)
                        if 2266 <= posx_value1 < 2832:
                            self.updateColor(13, scan_result)
                        if 2832 <= posx_value1 < 3398:
                            self.updateColor(14, scan_result)
                        if 3398 <= posx_value1 < 3964:
                            self.updateColor(15, scan_result)
                        if 3964 <= posx_value1 < 4530:
                            self.updateColor(16, scan_result)
                        if 4530 <= posx_value1 < 5100:
                            self.updateColor(17, scan_result)

        except Exception as e:
            print(f"Error in update_table: {e}")
            # self.inst_logger(f"{keys}")
            self.inst_logger.error(f"线程{self.__prc_name__}发生错误,错误为{traceback.format_exc()}")
            print(traceback.format_exc())

    def submit_clicked(self):
        try:
            # print(1)
            self.setFocus()
        except Exception as e:
            print(traceback.format_exc())

    def updateColor(self, name, result):
        # print(name, result)
        # 检查是否为绿色  如果是绿色 不覆盖 直接跳过

        name = str(name)
        frame = self.findChild(QFrame, name)
        if frame:
            # 应用样式表设置颜色
            frame.setStyleSheet(f"background-color: '{result}';")


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
    is_image = __ini_prc_config__.qt.image

    inst_logger.info("线程 %s 取得cli_id = %d" % (__prc_name__, __cli_id__))

    # 记录线程启动时间
    __prc_start_ts__ = datetime.datetime.now()
    inst_redis.setkey(f"pro_mon:{__prc_name__}:start_ts", __prc_start_ts__.isoformat())
    inst_logger.info("线程 %s 启动时间 start_ts= %s" % (__prc_name__, __prc_start_ts__.isoformat()))

    print("cli_manualscan start")
    # 创建条码显示窗口
    app = QApplication(sys.argv)
    barcode_display = BarcodeDisplay(inst_redis, __cli_id__, inst_logger, __prc_name__, __ini_prc_config__)
    barcode_display.show()
    inst_logger.info("线程 %s 已关闭窗口id = %d" % (__prc_name__, __cli_id__))
    sys.exit(app.exec_())
