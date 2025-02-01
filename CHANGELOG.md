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

Updated HIKCamera  

    communication function，barcode and heartbeat can send and recv by     pro_HIKCamera and write to stream_test in Redis

# Rev 0.2.5

Update HIKCamera,

    insert scan data into stream_test; 

    add throughput calc for short term and long term; 

    fix thread exit bug
Update fRedis

    lpush_ct calc and return avg_ct,max_ct
Fix fRedis xccreategroup bug

    when stream not existing, create an empty stream
Create stmHIKC data process

    read stream_test  and insert into key-value, if nr or mr ,slow down conv

# Rev 0.2.6

Create fBarcode 

    for barcode check(now empty)
Update HIKC 

    modify network thread, add unpack recv buf funtion, fix TCP Stick package bug

Create main_cli, prc_cli_manualscan

    get input barcode, 

    re function check barcode, 

    add ms barcode into stm_ms 

Create stm manualscan

    read from stm_ms and add to set.

# Rev 0.2.7

Update redis

    add keys function,read a list of keys by same prefix; using scan read result till return     value is 0
Update cli_ms

    get reading_gr/reading_mr,if read check ok, insert into stream ms
Fixed HIKC bug 

    heart interval in HIKC not refresh properly, keep send hearbeat and stick to other     TCP package

    update hearbeating function, when recv msg , no heartbeat send out
Update plc

    calc parcel position and write in to parce: posx :uid

    when calc parcel leave CV03, insert into stream reading confirm

# Rev 0.2.8

Update fRedis

    add clearset function, delete whole set
Update fPLC

    add autostart config and autostart function

    add autostop function

    fix bug from slow to highspeed continue output(is locked)
Update stmManualScan

    compare set_reading_nr/mr and set_ms_nr/mr, if ok move all code to set_reading_gr     and speed up conv,success

Try sys.exit(code), and catch exception in main()

# Rev 0.2.9

Update main_cli

    allow more than 1 cli running

    search running cli and find a right cli id , regist in Redis.
Update cli ms 

Create cli play sound

    using pygame play sound for scanner,stop playing if nr/mr happen ,success

Create media folder 

    using pygame play sound for manual scan ,including barcode exist, barcode not     valid, barcode valid, success 

# Rev 0.2.10

Create stm reading confirm
	get order info from stream and write into SQLite3 db
Fix cli_play and HIKC usde same consumer name ready stream bug
Fix stmHIKC bug
	before send slow speed command, check status; if conveyor already stopped , no need send any command .
Create ToDo List

# Rev 0.3.0
Update fRedis, 
	add lstException, add keysbuf, return keysbuf not keys-scan 
	add init_prc, all redis regist function inside. only need prc_name.
Update prc_template to 0.3.0
Update HIKCamera,PLC,stmHIKC,stmMS to template 0.3.0
Update fPLC function, reconstruct command and status,add autostart,autostop command.

# Rev 0.3.1
Add #client folder
	client computer run client in this folder. server run client in origin folder
Fix fRedis keysbuf bug
Fix cli_play MR sound bug
Update PLC, test and success, together update stmHIKC and stmManualScan,

# Rev 0.3.2
Add media to #client folder
	sys.path is not work when pygame get media files.

Not solve fRedis getkey--> key not existing fault, just comment this line
Add prc_mon, modify main.py, when enter 'Y', pro_mon send 'exit' comment and waiting for process cleanup and exit properly.

Update PLC, when exit stop all conv
Update stmHIKC_data, add redis exception print function,and exit function
Update stmManualScan, add redis exception print function,and exit function
Update stmReadingConfirm from template 2.0-->3.0

Add cli_qt, show parcel position and list, testing

# Rev 0.3.3
Update main_cli, add lst_thread, add exit code, add prc join, send syc:cli<xx>:comannd by "exit“ and clean sys：cli<xx>:ready

Update cli_ms to template 0.3, fix can not exit bug, add exit code and delete xgroup
update all stm relative py file, modified all xgroupcreate code , rest = none means no prolbem...，add exit code for xgroup delete
fix some group name fault

Add function for parcel position shown, on cli_qt

# Rev 0.4.0
Add stmHIKC_file, update main_cli_qt, Client show picture on the screen.direction and sequence config by ini file.

Update cli_ms, if set_reading_mr/nr is empty, do nothing.
	Maybe some bug, rest sentence will never run...

Temporary disable len = 0 clause in playsound. some bug may happen.

Dec stmHIKC_data CT from 1000 to 300,speed up to match high throughput

# Rev 0.4.1
Update fBarcode , and barcode_formatcheck_bylist, no test yet
Add stm_ReadingConfirm_dss, sync data with dss server
Update prc_PLC, main_cli_qt,stm_HIKC_data, add MS_AS function, manual scan after stop. manually solve stuck issue
Fix bug of manusal scan, after nr_ms and mr_ms, barcode should add into set_reading_gr

# Rev 0.4.2
Update cli_qt, ms_as mode, not all test success

# Rev 0.5.0
Update stm_ReadingConfirm, check db to order_info_ex,add batch_id for test;
select same batch_id and keep update count into redis sys:hawb:count
Update main,stm_ms,stm_hikc for sys:status,startup with 'idle', start run change to 'normal',find nr or mr change to 'alert', not ms on time(conveyor pause) change to 'stop', scan *enterclean* change to 'clean', scan  *endclean* change to normal

when status is not 'normal', sound and pic will not apply to normal parcel, only nr or mr.

Update client_qt,rewrith key_event.add code for enter and end clean mode, during clean mode no action really done(later need to add manual scan), when end clean mode, clean all nr,mr,ms_nr,ms_mr set, restart conv

add statusbar, show enter and leave clean mode; during clean mode show status and scanned barcode
fix bug of remover from deque
change ftp server to filezilla, ftp user ftp, no password

Update prc_plc, fix bug for posx still in list; delete posx before check parcel valid.if invalid parcel leave conveyor, only warning; 
add resume function, when endclean , conv resume when sys:status change to 'resume', after conv start, sys:status change to 'normal'

Update fHIKC, when receive MR, check if same barcode inside. if does, delete all same barcode.
# Rev 0.5.1
Update tp bar in QT, modify log size of main







