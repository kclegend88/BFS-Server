Key:
sys:device_name,string		 	# 设备名称，main.py首次连接redis时写入

pro_mon:<prc_name>:run_lock		# 现场运行锁，该key为空说明无此线程，如该线程为整数说明线程id为该整数的线程正在运行中;
								  每个线程均会判断这个key的状态，一旦发现该key不存在，将立刻终止当前线程

pro_mon:<prc_name>:restart		# 从main开始运行起，该线程启动的总次数，每重启一次加一
pro_mon:<prc_name>:start_ts		# 本线程启动的时间戳，ISO 8601格式记录的字符串
pro_mon:<prc_name>:lu_ts		# 本线程最近一次更新的时间戳，ISO 8601格式记录的字符串
pro_mon:<prc_name>:command		# 本线程的通知命令，任何外部线程如向此key写入"exit"，则该线程在完成必要操作后将自行结束线程

plc_conv:command				# start/stop，外部下发给PLC输送机(Conv)的运行命令
plc_conv:status					# pause/run，conv当前的运行状态
plc_conv:fullspeed				# Yes/No，conv是否全速运行的标志
plc_conv:CV01:speed				# CV01的速度,0 停止 1低速 2 低中速 3 4 修改redis中状态为高速

Set:
set_process						# 线程总清单,记录线程名称及线程id, 格式为：name=%s/id=%d

List:
lst_ct:<prc_name>				# 长度为10的数组，记录最近10次线程的cycle time