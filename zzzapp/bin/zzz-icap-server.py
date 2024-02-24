#!/opt/zzz/venv/bin/python3

#-----Zzz ICAP server daemon-----

import os
import signal
import site
import sys
import time

from pyicap import *

#-----make sure we're running as root or exit-----
# if os.geteuid()==0:
#     print('Zzz ICAP Server', flush=True)
# else:
#     sys.exit('This script must be run as root!')
print('Zzz ICAP Server', flush=True)

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.Config
import zzzevpn.ZzzICAPserver

#--------------------------------------------------------------------------------

should_run = True
should_reload = False

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

zzz_icap_server = zzzevpn.ZzzICAPserver.ZzzICAPserver(ConfigData)
zzz_icap_server.clear_data_log()
zzz_icap_server.start_server()

#--------------------------------------------------------------------------------

def signal_handler(signum, frame):
    if (signum == signal.SIGINT):
        print('Received SIGINT, exiting...', flush=True)
        zzz_icap_server.should_run(False)
        should_run = False
        raise Exception
    elif (signum == signal.SIGHUP):
        print('Received SIGHUP, reloading settings...', flush=True)
        zzz_icap_server.should_reload(True)
        should_reload = True
    # elif (signum == signal.SIGUSR1):
    #     print('Received SIGUSR1, exiting...', flush=True)
    #     zzz_icap_server.should_run(False)
    #     should_run = False
    #     raise Exception
    elif (signum == signal.SIGTERM):
        print('Received SIGTERM, exiting...', flush=True)
        zzz_icap_server.should_run(False)
        should_run = False
        raise Exception

#-----catch the reload-config signal (SIGHUP)-----
signal.signal(signal.SIGHUP, signal_handler)

#TODO: maybe remove this because using it may cause systemctl to get confused about daemon status
#  maybe adjust the auto-detect of an exited python script in the bash start-stop script
#-----catch Ctrl-C (SIGINT)-----
signal.signal(signal.SIGINT, signal_handler)

#-----catch SIGTERM (sent by the OS during system reboot/shutdown)-----
signal.signal(signal.SIGTERM, signal_handler)

#TODO: use this for something else in the future or remove it (only SIGTERM is used for shutdowns now)
#-----catch SIGUSR1-----
# signal.signal(signal.SIGUSR1, signal_handler)

#--------------------------------------------------------------------------------

datetime_now = zzz_icap_server.util.current_datetime()
print(f'Start zzz-icap-server {datetime_now}', flush=True)

#-----wait for a signal to quit-----
# while zzz_icap_server.should_run():
while should_run:
    # if zzz_icap_server.should_reload():
    if should_reload:
        print("Reloading settings...", flush=True)
        zzz_icap_server.reload_settings()
        should_reload = False
    try:
        sys.stderr.write('--------------------------------------------------------------------------------\n')
        #-----flush the buffers so output/error logs show results instantly-----
        sys.stdout.flush()
        sys.stderr.flush()
        zzz_icap_server.zzz_icap_threading.handle_request()
    except ICAPError as e:
        print("Caught ICAPError, continuing...", flush=True)
    except ConnectionResetError as e:
        print("Caught ConnectionResetError", flush=True)
    except Exception as e:
        print("Caught Exception, exiting...", flush=True)
        zzz_icap_server.should_run(False)
        should_run = False

#-----close cursor and DB when done using them-----
zzz_icap_server.db.db_disconnect()

datetime_now = zzz_icap_server.util.current_datetime()
print(f'Done zzz-icap-server {datetime_now}', flush=True)

#--------------------------------------------------------------------------------

