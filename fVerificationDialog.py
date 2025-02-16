import sys

from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt


class VerificationDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("包裹捕获确认")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 移除帮助按钮

        # 创建界面组件
        self.label = QLabel("请确认以下重要事项：\n\n此操作不可逆转！\n输入代码『CONFIRM』并回车以继续。")
        self.input_field = QLineEdit()
        self.cancel_btn = QPushButton("取消操作 (CANCEL)")

        # 设置组件属性
        self.input_field.setPlaceholderText("在此输入确认代码...")
        self.cancel_btn.setDefault(True)  # 设置取消为默认按钮

        # 创建布局
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input_field)
        layout.addWidget(self.cancel_btn)
        self.setLayout(layout)
        #
        # # 连接信号与槽
        self.input_field.returnPressed.connect(self.verify_code)
        #self.cancel_btn.clicked.connect(self.reject)
        #
        # # 自动聚焦输入框
        self.input_field.setFocus()

    def verify_code(self):
        """验证输入的代码是否正确"""
        if self.input_field.text() == "CONFIRM":
            self.accept()  # 输入正确时接受
        else:
            self.input_field.clear()
            self.input_field.setPlaceholderText("代码错误！请重新输入『CONFIRM』")
