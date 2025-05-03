# -*- coding: utf-8 -*-
import datetime
import sqlite3

class clsTrace:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(clsTrace, cls).__new__(cls)
            cls._instance.init(*args, **kwargs)
        return cls._instance
    def init(self, trace_file):
        self.trace_file = trace_file
        conn = sqlite3.connect(self.trace_file)
        cursor = conn.cursor()
        # self.conn = sqlite3.connect(trace_file)
        # self.cursor = self.conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS trace_table (INTUID INTEGER PRIMARY KEY AUTOINCREMENT,UID TEXT NOT NULL,THREAD TEXT,INFO TEXT,TS TEXT)')
        conn.close()
    def trace(self, str_uid,str_threadName,str_info):
        conn = sqlite3.connect(self.trace_file)
        cursor = conn.cursor()
        try:
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                'INSERT INTO trace_table (UID,THREAD,INFO,TS) VALUES (?,?,?,?)',
                (
                str_uid, str_threadName,str_info,current_time))
            # Only for debug
        except sqlite3.IntegrityError:
            print("************Trace_Fault**************")
        finally:
            conn.commit()
        conn.close()
        