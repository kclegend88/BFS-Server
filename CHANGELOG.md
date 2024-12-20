CHANGELOG

# Rev 0.1.0
Create main.ini
Create main.py	
	read ini,connect to redis

# Rev 0.1.1 
Create fLog.py, fConfig.py
	log to log\main.log,success
	log to screen,success

# Rev 0.1.2 
Create fRedis.py
	using default setting, connect to redis,success
	set redis key, success
	
# Rev 0.1.3 
Create prc_template V 0.1.0 
	copy prc_HIKCamera
	copy prc_PLC
	using lst_thread_name start all thread, success 

# Rev 0.2.0 
Create prc_template V 0.2.0 
	copy prc_HIKCamera
	copy prc_PLC
	create prc_HIKCamera.ini
	create prc_PLC.ini
	thread run_lock、get id from redis, lst_cycle_time, success
	
# Rev 0.2.1
Write fPLC process, main thread of PLC logi finished,need to upgrade;

# Rev 0.2.2
Write HIKCamera Network ,read success,not push into Redis yet
Fix fLog lineno and filename bug(stack level=2)