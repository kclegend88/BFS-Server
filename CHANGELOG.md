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

# Rev 0.2.3
Merge LQW prc_monitor and BFS, PLC and so on

# Rev 0.2.4
updated HIKCamera  communication function，barcode and heartbeat can send and recv by pro_HIKCamera and write to stream_test in Redis

# Rev 0.2.5
Update HIKCamera, insert scan data into stream_test; add throughput calc for short term and long term; fix thread exit bug
Update fRedis, lpush_ct calc and return avg_ct,max_ct
fix fRedis xccreategroup bug, when stream not existing, create an empty stream
Add stmHIKC data process, read stream_test  and insert into key-value, if nr or mr ,slow down conv

# Rev 0.2.6
create fBarcode for barcode check(now empty)
update HIKC network thread, add unpack recv buf funtion

add main_cli, prc_cli_manualscan, get input barcode, re function check barcode, add ms code into stm_ms 

add stm manualscan, read from stm_ms and add to set.

# Rev 0.2.7
Update redis, add keys function
Update cli_ms, get reading_gr/reading_mr,if read check ok, insert into stream ms
Fixed HIKC heart interval bug, when recv msg , no heartbeat send out
Update plc, calc parcel position,when leave CV03, insert into stream reading confirm
 
# Rev 0.2.8
Update fRedis, add clearset function
Update fPLC, add autostart config and autostart function,add autostop function,fix bug from slow to highspeed continue output
Update stmManualScan, compare set_reading_nr/mr and set_ms_nr/mr, if ok move all code to set_reading_gr and speed up conv,success
try sys.exit(code), and catch exception in main()

