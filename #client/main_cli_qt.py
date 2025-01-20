# prc_template  v 0.2.0
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
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QPalette, QBrush
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
            # 读取配置文件
            self.is_image = __ini_prc_config__.qt.image
            self.level = __ini_prc_config__.qt.level
            self.pic_direction = __ini_prc_config__.qt.pic_direction
            self.all_show_flag = __ini_prc_config__.qt.all_show_flag
            self.server_ip = __ini_prc_config__.qt.server_ip
            self.pic_rotate = __ini_prc_config__.qt.pic_rotate
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
            self.inst_logger.info("线程 %s 注册stream组成功" % (__prc_name__,))
            self.uid_deque = deque()
            try:
                inst_redis.xcreategroup(self.stream_name_create, self.__prc_name__)
                inst_logger.info("线程 %s 注册stream组成功" % (__prc_name__,))
            except Exception as e:
                inst_logger.info("线程 %s 注册stream组失败，该组已存在" % (__prc_name__,))
            try:
                inst_redis.xcreategroup(self.stream_name_delete, self.__prc_name__)
                inst_logger.info("线程 %s 注册stream组成功" % (__prc_name__,))
            except Exception as e:
                inst_logger.info("线程 %s 注册stream组失败，该组已存在" % (__prc_name__,))
            self.init_ui()

        def addImageToFrame(self, frame_name, i, barcode):
            # 使用对象名找到相应的 QFrame

            image = QPixmap(f"{i}")  # i 是图片的路径
            pixmap = image.scaled(600, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if self.pic_rotate == 1:
                # 创建 QTransform 对象用于旋转 180 度
                transform = QTransform()
                transform.rotate(180)  # 旋转 180 度

                # 使用 QMatrix 对象来变换 QPixmap
                rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
                # 在 QPixmap 上绘制条形码
                painter = QPainter(rotated_pixmap)
            else:
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
            # self.btn_submit.setFixedSize(100, 40)  # 设置按钮大小
            self.btn_submit.clicked.connect(self.submit_clicked)
            leftlayout.addLayout(self.pic_layout, 3)
            leftlayout.addWidget(self.label, 1)  # 设置比例
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
            # 启动一个线程，接收stream数据 并且更新图片
            thread = threading.Thread(target=self.pic_show)
            # 设置线程为守护线程
            thread.daemon = True
            thread.start()
            # 最大化
            #self.showMaximized()
            self.showFullScreen()
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
                        self.scanbarcode = self.barcode_input
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
            # 如command区收到退出命令，根据线程类型决定是否立即退出
            prc_run_lock = self.inst_redis.getkey(f"sys:cli{self.__cli_id__:02}:command")
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
            #keys = self.inst_redis.keys('parcel:scan_result:*')
            # keys = self.inst_redis.getbuff('parcel:scan_result:*')
            # 存储结果的列表
            results = []
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
                # 如果补码的值与barcode一样  将table变色
                try:
                    if result['barcode'] == self.scanbarcode:
                        item = self.tableWidget.item(row, 0)
                        item.setBackground(QBrush(QColor(255, 105, 180)))  # 背景颜色
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

    def submit_clicked(self):
        try:
            current_barcode = '##' + self.input.text()
            self.inst_logger.info(f"手动提交的条码：{current_barcode}")
            self.input.setText('')
            self.update_barcode(current_barcode)
            self.setFocus()
        except Exception as e:
            print(traceback.format_exc())

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
                        self.inst_logger.info("stream_test收到序列 %s 中的消息累计 %d 行" % (stream_test[0][0], len(stream_test[0][1])))
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
                                if not self.all_show_flag:
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
        for i in range(10):
            time.sleep(0.5)
            # 连接到FTP服务器
            ip = self.server_ip
            ftp = FTP(ip)  # 服务器地址
            ftp.login('HPSERVER', 'analog.1')  # 使用正确的用户名和密码
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

    inst_logger.info("cli_manualscan start")
    # 创建条码显示窗口
    app = QApplication(sys.argv)
    barcode_display = BarcodeDisplay(inst_redis, __cli_id__, inst_logger, __prc_name__, __ini_prc_config__)
    barcode_display.show()
    sys.exit(app.exec_())

    def pic_show(self):
        self.addImageToFrame(f"frame_{1}", 1)
        self.addImageToFrame(f"frame_{2}", 2)
        self.addImageToFrame(f"frame_{0}", 0)
