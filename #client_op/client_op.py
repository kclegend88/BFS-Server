import sys
import json
import sqlite3
import pandas as pd
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QHBoxLayout,
                             QPushButton, QMessageBox, QHeaderView,
                             QFileDialog, QComboBox, QLabel, QLineEdit,
                             QAbstractItemView)
from PyQt5.QtCore import QTimer, QUrl, Qt, QSettings
from PyQt5.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt5.QtGui import QBrush, QColor
from fRedis import clsRedis
from fLog import clsLogger
from fConfig import clsConfig

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mb_data = []
        self.hb_data = {}  # {MBID: [hb1, hb2...]}
        self.current_mbid = None
        self.current_hb_filter = None
        self.db_path = ""
        self.setup_ui()
        self.setup_network()
        self.setup_timer()
        self.load_settings()
        self.ini_config = clsConfig('main.ini')
        self.inst_logger = clsLogger(self.ini_config)
        self.inst_redis = clsRedis(self.ini_config)
        self.inst_logger.info("main 线程启动")

        # 读取配置文件
        try:
            __device_name__= self.ini_config.Name.Device_Name
        except:
            self.inst_logger.error("配置读取失败"+traceback.format_exc())
            input("从ini文件中读取配置信息失败,请按任意键....")
        self.inst_logger.info("配置与日志初始化成功")

    def setup_ui(self):
        self.setWindowTitle("主单管理")
        self.resize(1200, 800)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 数据源选择栏
        source_layout = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItems(["网络接口", "本地数据库", "文件导入"])
        self.source_combo.currentIndexChanged.connect(self.change_data_source)
        source_layout.addWidget(QLabel("数据源:"))
        source_layout.addWidget(self.source_combo, 1)

        # 数据库路径组件
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setPlaceholderText("数据库路径")
        self.db_browse_btn = QPushButton("浏览...")
        self.db_browse_btn.clicked.connect(self.select_db_file)
        source_layout.addWidget(QLabel("数据库路径:"))
        source_layout.addWidget(self.db_path_edit, 3)
        source_layout.addWidget(self.db_browse_btn, 1)

        # 文件导入组件
        self.import_mb_btn = QPushButton("导入主单文件")
        self.import_hb_btn = QPushButton("导入分单文件")
        self.import_mb_btn.clicked.connect(lambda: self.import_file('MB'))
        self.import_hb_btn.clicked.connect(lambda: self.import_file('HB'))
        source_layout.addWidget(self.import_mb_btn)
        source_layout.addWidget(self.import_hb_btn)
        
        main_layout.addLayout(source_layout)

        # 主内容区域
        content_layout = QHBoxLayout()
        
        # 主单列表
        self.mb_table = QTableWidget()
        self.mb_table.setColumnCount(4)
        self.mb_table.setHorizontalHeaderLabels(["MBID", "别名", "重量", "时间"])
        self.mb_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mb_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mb_table.clicked.connect(self.on_mb_clicked)
        content_layout.addWidget(self.mb_table, 40)

        # 右侧区域
        right_layout = QVBoxLayout()
        
        # 统计表格
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["状态", "数量"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.clicked.connect(self.on_stats_clicked)
        right_layout.addWidget(self.stats_table, 30)

        # 分单详情表格
        self.hb_detail_table = QTableWidget()
        self.hb_detail_table.setColumnCount(4)
        self.hb_detail_table.setHorizontalHeaderLabels(["HBID", "状态", "清关状态", "关联主单"])
        self.hb_detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hb_detail_table.setSortingEnabled(True)
        right_layout.addWidget(self.hb_detail_table, 70)

        self.send_btn = QPushButton("发送数据")
        self.send_btn.setEnabled(True)
        self.send_btn.clicked.connect(self.send_data)
        right_layout.addWidget(self.send_btn)

        self.read_btn = QPushButton("读取数据")
        self.read_btn.setEnabled(True)
        self.read_btn.clicked.connect(self.read_data)
        right_layout.addWidget(self.read_btn)

        self.save_btn = QPushButton("保存数据")
        self.save_btn.setEnabled(True)
        self.save_btn.clicked.connect(self.save_data)
        right_layout.addWidget(self.save_btn)

        content_layout.addLayout(right_layout, 60)
        main_layout.addLayout(content_layout)

    def setup_network(self):
        self.network = QNetworkAccessManager()
        
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.fetch_data)
        self.timer.start(5000)

    def change_data_source(self, index):
        """切换数据源时更新控件状态"""
        # 0: 网络 1: 数据库 2: 文件
        self.timer.stop() if index != 0 else self.timer.start()
        self.db_path_edit.setEnabled(index == 1)
        self.db_browse_btn.setEnabled(index == 1)
        self.import_mb_btn.setEnabled(index == 2)
        self.import_hb_btn.setEnabled(index == 2)
        self.fetch_data()

    def import_file(self, file_type):
        """导入CSV/Excel文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, f"选择{file_type}文件", "",
            "数据文件 (*.csv *.xlsx *.xls)"
        )
        if not path:
            return
        try:
            if path.endswith('.csv'):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)
            data = df.to_dict(orient='records')
            if file_type == 'MB':
                self.mb_data = data
                self.update_mb_table()
            elif file_type == 'HB':
                # 按MBID重新组织分单数据
                print(data)
                self.hb_data.clear()
                for hb in data:
                    mbid = hb.get('MBID')
                    if mbid not in self.hb_data:
                        self.hb_data[mbid] = []
                    self.hb_data[mbid].append(hb)
                
                if self.current_mbid:
                    self.update_stats(self.current_mbid)
                    self.update_hb_detail_table()

        except Exception as e:
            QMessageBox.critical(self, "导入错误", f"文件读取失败:\n{str(e)}")

    def update_hb_detail_table(self, filter_status=None):
        """更新分单详情表格"""
        mbid = self.current_mbid
        hb_list = self.hb_data.get(mbid, [])
        
        # 应用状态筛选
        if filter_status:
            hb_list = [hb for hb in hb_list if hb.get('HBStatus') == filter_status]
        
        self.hb_detail_table.setRowCount(len(hb_list))
        for row, hb in enumerate(hb_list):
            items = [
                QTableWidgetItem(str(hb.get('HBID', ''))),
                QTableWidgetItem(hb.get('HBStatus', '')),
                QTableWidgetItem(hb.get('HBCustom', '')),
                QTableWidgetItem(str(hb.get('MBID', '')))
            ]
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.hb_detail_table.setItem(row, col, item)

    def on_stats_clicked(self, index):
        """点击统计表格时筛选分单详情"""
        status_item = self.stats_table.item(index.row(), 0)
        if status_item:
            self.current_hb_filter = status_item.text()
            self.update_hb_detail_table(self.current_hb_filter)

    def on_mb_clicked(self, index):
        """点击主单时更新统计和详情"""
        row = index.row()
        self.current_mbid = self.mb_table.item(row, 0).text()
        self.current_hb_filter = None  # 清除筛选状态
        self.update_stats(self.current_mbid)
        self.update_hb_detail_table()

    def update_stats(self, mbid):
        """更新统计表格（原有逻辑优化）"""
        hb_list = self.hb_data.get(mbid, [])
        status_count = {}
        for hb in hb_list:
            status = hb.get('HBStatus', 'Unknown')
            status_count[status] = status_count.get(status, 0) + 1

        self.stats_table.setRowCount(len(status_count))
        for row, (status, count) in enumerate(status_count.items()):
            self.stats_table.setItem(row, 0, QTableWidgetItem(status))
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(count)))
            # 高亮OK状态
            if status == 'OK':
                for col in range(2):
                    self.stats_table.item(row, col).setBackground(QBrush(QColor(144, 238, 144)))

        # 检查OK状态是否超过90%
        total = len(hb_list)
        ok = status_count.get('OK', 0)
        # self.send_btn.setEnabled(total > 0 and (ok / total) >= 0.9)
        self.update_hb_detail_table()

    def fetch_data(self):
        if self.source_combo.currentIndex() == 0:
            self.fetch_mb_data_network()
        else:
            self.fetch_mb_data_local()

    def fetch_mb_data_network(self):
        url = QUrl("http://example.com/FastScan/get_mbinfo")
        request = QNetworkRequest(url)
        reply = self.network.get(request)
        reply.finished.connect(lambda: self.handle_mb_reply(reply))

    def fetch_mb_data_local(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MBID, MBAlias, MBWeight, MBTime FROM MB_Info")
            self.mb_data = [{
                "MBID": row[0],
                "MBAlias": row[1],
                "MBWeight": row[2],
                "MBTime": row[3]
            } for row in cursor.fetchall()]

            # 获取所有分单数据
            self.hb_data.clear()
            for mb in self.mb_data:
                cursor.execute("SELECT HBID, HBStatus, HBCustom FROM HB_Info WHERE MBID=?", (mb["MBID"],))
                self.hb_data[mb["MBID"]] = [{
                    "HBID": row[0],
                    "HBStatus": row[1],
                    "HBCustom": row[2],
                    "MBID": mb["MBID"]
                } for row in cursor.fetchall()]

            conn.close()
            self.update_mb_table()
            if self.current_mbid:
                self.update_stats(self.current_mbid)
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"无法读取数据库:\n{str(e)}")

    def handle_mb_reply(self, reply):
        if reply.error() == QNetworkReply.NoError:
            data = json.loads(reply.readAll().data())
            self.mb_data = data
            self.update_mb_table()
            # 获取所有分单数据
            for mb in self.mb_data:
                self.fetch_hb_data_network(mb['MBID'])
        else:
            QMessageBox.warning(self, "错误", "获取主单数据失败")
        reply.deleteLater()

    def fetch_hb_data_network(self, mbid):
        url = QUrl(f"http://example.com/FastScan/get_hbinfo?mbid={mbid}")
        request = QNetworkRequest(url)
        reply = self.network.get(request)
        reply.finished.connect(lambda: self.handle_hb_reply(reply, mbid))

    def handle_hb_reply(self, reply, mbid):
        if reply.error() == QNetworkReply.NoError:
            data = json.loads(reply.readAll().data())
            self.hb_data[mbid] = data
            if self.current_mbid == mbid:
                self.update_stats(mbid)
        else:
            QMessageBox.warning(self, "错误", f"获取分单数据失败：{mbid}")
        reply.deleteLater()

    def update_mb_table(self):
        self.mb_table.setRowCount(len(self.mb_data))
        for row, mb in enumerate(self.mb_data):

            items = [
                QTableWidgetItem(mb.get('MBID', '')),
                QTableWidgetItem(mb.get('MBAlias', '')),
                QTableWidgetItem(mb.get('MBWeight', '')),
                QTableWidgetItem(mb.get('MBTime', ''))
            ]

            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.mb_table.setItem(row, col, item)

    def read_data(self):
        if not self.current_mbid:
            return
        # 尝试连接Redis
        try:
            self.inst_redis.connect(self.ini_config)
            if self.inst_redis.lstException:  # 取得异常消息队列中的信息
                for i, e in enumerate(self.inst_redis.lstException):
                    self.inst_logger.error(
                        "主线程连接 Redis 服务器失败，调用模块 %s，调用时间 %s，异常信息 %s "
                        % (e['module'], e['timestamp'], e['msg']))
                self.inst_redis.lstException.clear()
            self.inst_logger.info("Redis 连接成功")
        except Exception as e:
            self.inst_logger.error("Redis连接过程中发生异常:" + traceback.format_exc())
            QMessageBox.information(self, "失败", "数据库无法正常链接")
            return
        # 更新本地数据
        mbid = self.inst_redis.getkey('sys:batchid')
        bmbidfound = False
        for mbinfo in self.mb_data:
            if mbid== mbinfo['MBID']:
                bmbidfound = True

        if not bmbidfound:
            self.inst_logger.error("主单编号 %s 不在当前主单列表中 %s"%(mbid,self.mb_data))
            QMessageBox.information(self, "失败", "服务器上的MAWB与本机数据不符")
            return
        hawb_keys = self.inst_redis.keys('hawb:status:*')
        if hawb_keys:
            self.inst_logger.info("共有 %s 个分单信息" % (len(hawb_keys)))
        update_counter = 0
        for key in hawb_keys:
            parts = key.split(':')  # 分割键名 parts[0]='hawb', parts[1]='status',parts[2] 为 barcode
            barcode = parts[2]
            bhbidfound = False
            searchcounter = 0
            for hawb in self.hb_data[mbid]:
                searchcounter = searchcounter + 1
                if barcode == hawb['HBID']:
                    bhbidfound = True
                    status_old = hawb['HBStatus']
                    status_new = self.inst_redis.getkey(key)
                    if status_old == status_new:  # 该hawb状态未更新
                        continue
                    self.inst_logger.info("分单 %s 状态由 %s 更新为 %s" % (barcode, status_old, status_new))
                    hawb['HBStatus'] = status_new
                    update_counter = update_counter + 1
                    break
            if not bhbidfound:
                self.inst_logger.info("本运单 %s 在本地数据库中未找到记录,搜索 %s 次" % (barcode,searchcounter))

        self.inst_logger.info("累计更新分单状态 %s 条" % (update_counter,))
        self.update_mb_table()
        if self.current_mbid:
            self.update_stats(self.current_mbid)
    def send_data(self):
        if not self.current_mbid:
            return
        # 尝试连接Redis
        try:
            self.inst_redis.connect(self.ini_config)
            if self.inst_redis.lstException:  # 取得异常消息队列中的信息
                for i, e in enumerate(self.inst_redis.lstException):
                    self.inst_logger.error(
                        "主线程连接 Redis 服务器失败，调用模块 %s，调用时间 %s，异常信息 %s "
                        % (e['module'], e['timestamp'], e['msg']))
                self.inst_redis.lstException.clear()
            self.inst_logger.info("Redis 连接成功")
        except Exception as e:
            self.inst_logger.error("Redis连接过程中发生异常:"+traceback.format_exc())
            QMessageBox.information(self, "失败", "数据库无法正常链接")
            return
        # 判断输送机状态，如果为pause 不传输
        # 判断包裹状态 如果parcel中有包裹，不传输
        # 判断set_check_ng_catch状态，需要全部扫描后清理该set再传输
        # 判断set_reading_mr\nr set_check_ng状态，如果不为空，不传输
        # 读取当前mawb状态，确认总单完成清， 如果未全部完成 弹出窗口要求确认
        # 清理set_reading_gr\set_check_ng_catch
        # 发送转存命令，服务器将当前mawb操作记录，异地存储后清理db文件
        self.inst_redis.clearset("set_reading_gr")
        self.inst_redis.clearset("set_check_ng_catch")
        self.inst_redis.clearset("set_hawb_rj")
        self.inst_redis.clearset("set_reading_gr")

        mb_info = next((mb for mb in self.mb_data if mb['MBID'] == self.current_mbid), None)
        if not mb_info:
            return

        data = self.hb_data.get(self.current_mbid, [])
        self.inst_redis.clearset("set_hawb")
        
        for i, item in enumerate(data):
            self.inst_redis.sadd("set_hawb",item['HBID'])
            self.inst_redis.setkey(f"hawb:status:{item['HBID']}",item['HBStatus'])
            if item['HBStatus'] in ['800','900','901','950']:
                self.inst_redis.sadd('set_hawb_rj',item['HBID'])

        self.inst_redis.setkey("sys:batchid",self.current_mbid)

        QMessageBox.information(self, "成功", "数据已发送")

    def save_data(self):
        if not self.current_mbid or self.source_combo.currentIndex() != 1:
            return

        confirm = QMessageBox.question(
            self,
            "确认更新",
            "确定要将当前分单状态更新到数据库吗？此操作不可逆！",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            hb_list = self.hb_data.get(self.current_mbid, [])
            if not hb_list:
                QMessageBox.information(self, "提示", "没有可更新的分单数据")
                return

            # 准备批量更新数据
            update_data = [(hb['HBStatus'], hb['HBID']) for hb in hb_list]

            # 执行事务更新
            cursor.executemany(
                "UPDATE HB_Info SET HBStatus = ? WHERE HBID = ?",
                update_data
            )
            conn.commit()

            # 刷新本地缓存
            self.fetch_hb_data_local(self.current_mbid)

            # 更新界面显示
            self.update_stats(self.current_mbid)
            self.update_hb_detail_table()

            QMessageBox.information(self, "成功", "已成功更新 {} 条分单状态".format(len(hb_list)))

        except sqlite3.Error as e:
            QMessageBox.critical(self, "数据库错误", f"更新失败:\n{str(e)}")
            if conn:
                conn.rollback()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生未知错误:\n{str(e)}")
        finally:
            if conn:
                conn.close()

    def fetch_hb_data_local(self, mbid):
        """从本地数据库重新加载指定主单的分单数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT HBID, HBStatus, HBCustom FROM HB_Info WHERE MBID=?", (mbid,))
            self.hb_data[mbid] = [{
                "HBID": row[0],
                "HBStatus": row[1],
                "HBCustom": row[2],
                "MBID": mbid
            } for row in cursor.fetchall()]
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"刷新数据失败:\n{str(e)}")
    def load_settings(self):
        settings = QSettings("MyCompany", "MyApp")
        self.db_path = settings.value("db_path", "")
        self.db_path_edit.setText(self.db_path)
        self.source_combo.setCurrentIndex(int(settings.value("data_source", 0)))

    def save_settings(self):
        settings = QSettings("MyCompany", "MyApp")
        settings.setValue("db_path", self.db_path)
        settings.setValue("data_source", self.source_combo.currentIndex())
    def select_db_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择数据库文件", "", "SQLite数据库 (*.db *.sqlite)")
        if path:
            self.db_path = path
            self.db_path_edit.setText(path)
            self.save_settings()
            self.fetch_data()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())