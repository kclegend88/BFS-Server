# Key:
**sys:ready**: True/False
	设备主程序运行标志位  
**sys:device_name**: string
	设备名称，main.py首次连接redis时写入
**sys:status**: string
	设备状态
	idle:程序启动时默认状态
	normal:正常状态，输送机全速运行，自动读码
	alert:警报，输送机低速运行，手动补码至恢复normal状态
	stop:停止，输送机停止，可继续补码
	clean:清场，输送机停止后，刷清场码进入该状态，逐个扫描包裹
	resume:重启，10s启动cv3，之后启动cv2，在此期间如果接收到扫码信息，报错停机	
**pro_mon:`<prc_name>`:run_lock**: int
	现场运行锁，该key为空说明无此线程，如该线程为整数说明线程id为该整数的线程正在运行中;
	每个线程均会判断这个key的状态，一旦发现该key不存在，将立刻终止当前线程
**pro_mon:`<prc_name>`:restart**: int
	从main开始运行起，该线程启动的总次数，每重启一次加一
**pro_mon:`<prc_name>`:start_ts**: datetime isoformat
	本线程启动的时间戳，ISO 8601格式记录的字符串
**pro_mon:`<prc_name>`:lu_ts**: datetime isoformat
	本线程最近一次更新的时间戳，ISO 8601格式记录的字符串
**pro_mon:`<prc_name>`:command**
	本线程的通知命令，任何外部线程如向此key写入"exit"，则该线程在完成必要操作后将自行结束线程
**plc_conv:command**: string 
	start:	所有输送机全部启动
	stop: 所有输送机全部停止	
	外部下发给PLC输送机(Conv)的运行命令
plc_conv:status                    # pause/run，conv当前的运行状态
plc_conv:fullspeed                # Yes/Countdown，conv是否全速运行的标志
plc_conv:CV01:speed                # CV01的速度,0 停止 1低速 2 低中速 3 4 修改redis中状态为高速

tp: scanner_tp_short:lu_ts        # 用于计算scanner流量的luts
tp: scanner_tp_short:counter        # 读码报文计数器 也用于生成tp_long的辅助计数器
tp: short						# 短期折算流量(件/小时) -10 pcs
tp: long						# 短期折算流量(件/小时) -100 pcs

parcel: barcode:<uid>            # 指定扫描uid得到的条码
parcel: sid:<uid>                # 指定扫描uid 在stream_test中的stream id，用于后续删除stream中的对象
parcel: posx:<uid>                # 指定扫描uid的x坐标，随PLC转动不断更新
parcel: posy:<uid>                # 指定扫描uid的y坐标，不会更新
parcel: scan_result:<uid>        # 指定扫描uid的扫描结果，GR/MR/NR
parcel: check_result:<uid>		 # 指定uid的hawb核查结果；

hawb:status:<barcode>			# 300-900的数值
hawb:check_result:<barcode>		# 该单号本批次的核查结果

Set:
set_hawb						 # 当前主单下所有分单的集合
set_process                        # 线程总清单,记录线程名称及线程id, 格式为：name=%s/id=%d
set_reading_gr                    # 扫描结果为GR的集合
set_reading_mr                    # 扫描结果为MR的集合
set_reading_nr                    # 扫描结果为NR的集合
set_check_ok						# Barcode Check 返回的正常包裹
set_check_ng						# Barcode Check 返回的异常
set_check_ng_catch					# Barcode Check 返回异常后，已被操作人员捕获

List:
lst_ct:<prc_name>                # 长度为10的数组，记录最近10次线程的cycle time
lst_ct:scanner_tp_short            # 长度为10的数组，记录读码报文返回的cycle time MR/GR/NR每件都算
lst_ct:scanner_tp_long            # 长度为10的数组，scanner_tp_short中每10个包裹的平均ct作为元素

Stream:
stream_test                        # 测试用stream 
                                ['uid']        :36位uid MR时带后缀 -0 -1 -2....
                                ['req_ts']    :时间戳 
                                ['code']    :条码 NR时为空
                                ['result']    :读码结果 GR/MR/NR
                                ['pos_x']    :输送方向坐标，从RGBD原点开始计算，发送报文应为1700左右 
                                ['pos_y']    :宽度方向坐标，从RGBD 原点开始计算，前进右侧为正
			group: HIKC, prc: stmHIKC_data, client : HIKC_data-id01
			group: cli<xx>_playsound, prc: cli_playsound, client : cliplay-id01		
stream_buf                        # 调试用stream
                                ['buf'] = 'read'
                                ['data'] = b''    : recv_buf中收到的数据
stream_reading_confirm            # 已经确认的条码 
                                ['uid']        :36位uid MR时带后缀 -0 -1 -2....
                                ['ts']        :确认的时间戳 
                                ['barcode']    :条码
                                ['scan_result']        :读取结果，GR/MR_MS/NR_MS
                                ['check_result']    :检查结果，OK/RC/BL/OP/NF/SF
                                ['remark']            :用来存补码的过程的，包括cli_id, scan_id 等;
			group: ReadingConfirm, prc:stmReadingConfirm, client :ReadingConfirm-DB01

stream_manualscan                # 测试用stream 
                                ['cli_id']    :客户端编号
                                ['scan_id']    :扫描编号 
                                ['barcode']    :条码
                                ['type']    :MR/NR
			group: manualscan, prc: stmManualScan, client: manualscan-id01