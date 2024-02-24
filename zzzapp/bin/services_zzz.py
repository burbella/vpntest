#!/opt/zzz/venv/bin/python3

#-----Zzz core services daemon-----
# It must run as root to perform various tasks
# It sleeps 1 second, then wakes up and checks the DB for work

import decimal
import os
import signal
import site
import sys
import time

#-----run at minimum priority-----
os.nice(19)

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz daemon startup', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.Config
# import zzzevpn.ServiceRequest

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

service_request = zzzevpn.ServiceRequest(ConfigData)

#---------------------------------------------------------------------------------------------------

def optimize_db(service_request: zzzevpn.ServiceRequest, time_last_optimize: float):
    datetime_now_str = service_request.util.current_datetime()
    print(f'optimize DB start: {datetime_now_str}', flush=True)

    service_request.util.set_db_maintenance_flag('db_optimize')
    try:
        service_request.db.optimize()
    except:
        print('ERROR: db.optimize() crashed')
    # make sure the flag gets cleared whether the DB operation worked or not
    service_request.util.clear_db_maintenance_flag()

    # count the runtime
    dec_start = decimal.Decimal().from_float(time_last_optimize)
    dec_end = decimal.Decimal().from_float(time.time())
    optimize_runtime = round(dec_end - dec_start, 6)
    print(f'optimize DB runtime: {optimize_runtime} seconds', flush=True)

#---------------------------------------------------------------------------------------------------

#  1) SIGHUP       2) SIGINT       3) SIGQUIT      4) SIGILL       5) SIGTRAP
#  6) SIGABRT      7) SIGBUS       8) SIGFPE       9) SIGKILL     10) SIGUSR1
# 11) SIGSEGV     12) SIGUSR2     13) SIGPIPE     14) SIGALRM     15) SIGTERM
# 16) SIGSTKFLT   17) SIGCHLD     18) SIGCONT     19) SIGSTOP     20) SIGTSTP
# 21) SIGTTIN     22) SIGTTOU     23) SIGURG      24) SIGXCPU     25) SIGXFSZ
# 26) SIGVTALRM   27) SIGPROF     28) SIGWINCH    29) SIGIO       30) SIGPWR
# 31) SIGSYS      34) SIGRTMIN    35) SIGRTMIN+1  36) SIGRTMIN+2  37) SIGRTMIN+3
# 38) SIGRTMIN+4  39) SIGRTMIN+5  40) SIGRTMIN+6  41) SIGRTMIN+7  42) SIGRTMIN+8
# 43) SIGRTMIN+9  44) SIGRTMIN+10 45) SIGRTMIN+11 46) SIGRTMIN+12 47) SIGRTMIN+13
# 48) SIGRTMIN+14 49) SIGRTMIN+15 50) SIGRTMAX-14 51) SIGRTMAX-13 52) SIGRTMAX-12
# 53) SIGRTMAX-11 54) SIGRTMAX-10 55) SIGRTMAX-9  56) SIGRTMAX-8  57) SIGRTMAX-7
# 58) SIGRTMAX-6  59) SIGRTMAX-5  60) SIGRTMAX-4  61) SIGRTMAX-3  62) SIGRTMAX-2
# 63) SIGRTMAX-1  64) SIGRTMAX

#TODO: consider switching to SIGUSR1 and SIGUSR2 for reload/shutdown signals as a daemon
def signal_handler(signum, frame):
    if (signum == signal.SIGINT):
        print('Received SIGINT, exiting...', flush=True)
        service_request.should_run(False)
    elif (signum == signal.SIGHUP):
        print('Received SIGHUP, config reload not implemented yet', flush=True)
        # print('Received SIGHUP, reloading config...', flush=True)
        # service_request.should_reload(True)
    elif (signum == signal.SIGUSR1):
        print('Received SIGUSR1, setting the checkwork flag...', flush=True)
        service_request.should_checkwork(True)
    elif (signum == signal.SIGTERM):
        print('Received SIGTERM, exiting...', flush=True)
        service_request.should_run(False)

#-----catch the reload-config signal (SIGHUP)-----
signal.signal(signal.SIGHUP, signal_handler)

#-----catch Ctrl-C (SIGINT), used to stop the daemon-----
signal.signal(signal.SIGINT, signal_handler)

#-----catch SIGTERM (sent by the OS during system reboot/shutdown)-----
signal.signal(signal.SIGTERM, signal_handler)

#-----catch the checkwork signal (SIGUSR1)-----
signal.signal(signal.SIGUSR1, signal_handler)

#---------------------------------------------------------------------------------------------------

#-----initialize the work_available table-----
service_request.util.work_available(True)
service_request.zzz_redis.zzz_checkwork_set()

datetime_now_str = service_request.util.current_datetime()
print(f'Start services_zzz {datetime_now_str}', flush=True)

time_last_log_entry = time.time()
time_last_optimize = time.time()
time_since_db_check = 0
three_hours = 3600*3

decimal.getcontext().prec = 6

#-----wait for a signal to quit-----
while service_request.should_run():
    #-----look at the checkwork flags in memory/redis every 0.1 seconds to make the daemon more responsive-----
    # only check the DB flag once every 10 seconds to keep the DB query load down
    # the redis flag should work all the time, but the DB is a backup
    # the memory flag only works when a root process is sending a SIGUSR1 signal
    time_now = time.time()
    if (time_now-time_since_db_check)<10:
        #-----only check memory/redis flags most of the time-----
        if service_request.should_checkwork() or service_request.zzz_redis.zzz_checkwork_get():
            service_request.check_for_work()
    else:
        #-----DB flag check (check memory/redis flags first in case they are set)-----
        time_since_db_check = time_now
        if service_request.should_checkwork() or service_request.zzz_redis.zzz_checkwork_get() or service_request.util.work_available():
            service_request.check_for_work()

    # print something to the log hourly, even if nothing is going on
    if (time_now-time_last_log_entry)>3600:
        datetime_now_str = service_request.util.current_datetime()
        print(f'keepalive {datetime_now_str}', flush=True)
        time_last_log_entry = time_now

    # optimize the DB every 3 hours, but not if some other DB maintenance is going on
    if (time_now-time_last_optimize)>three_hours:
        if service_request.util.check_db_maintenance_flag():
            # wait 10 seconds before checking for the flag again
            time_last_optimize = three_hours - 10
        else:
            time_last_optimize = time.time()
            optimize_db(service_request, time_last_optimize)

    time.sleep(0.2)

#-----close cursor and DB when done using them-----
service_request.db.db_disconnect()

datetime_now_str = service_request.util.current_datetime()
print(f'Done services_zzz {datetime_now_str}', flush=True)
