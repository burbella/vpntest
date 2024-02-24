#!/opt/zzz/venv/bin/python3

#-----IP Log processing-----
# this will be called a cron
# need to process IP logs frequently to keep DB table data recent for viewing
# keep a record of the time of the last packet processed, so no duplicates are processed

import argparse
import os
import site
import sys
import time

#-----run at minimum priority-----
os.nice(19)

#-----make sure we're running as root or exit-----
if os.geteuid()!=0:
    sys.exit('This script must be run as root!')

print('Zzz iptables processing', flush=True)

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.Config
# import zzzevpn.IPtablesLogParser

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

#-----read command-line options-----
# can only do one at a time
# actions: init, summary, update
arg_parser = argparse.ArgumentParser(description='Update IP Logs in DB')
arg_parser.add_argument('-i', '--init', dest='init', action='store_true', help='clear the DB and initialize it from all logs (effectively delete-update-summary)')
arg_parser.add_argument('-c', '--country', dest='country', action='store_true', help='update country codes in IP logs')
arg_parser.add_argument('-s', '--summary', dest='summary', action='store_true', help='process daily logs into the DB summary table')
arg_parser.add_argument('-u', '--update', dest='update', action='store_true', help='update the IP Log DB')
args = arg_parser.parse_args()

action_count = 0
if args.init:
    action_count += 1
    print('  action: INIT')
if args.country:
    action_count += 1
    print('  action: COUNTRY')
if args.summary:
    action_count += 1
    print('  action: SUMMARY')
if args.update:
    action_count += 1
    print('  action: UPDATE')
if action_count > 1:
    print('ERROR: only one action allowed at a time (INIT, COUNTRY, SUMMARY, UPDATE)')
    sys.exit()
if action_count == 0:
    arg_parser.print_help()
    sys.exit()

iptables_log_parser = zzzevpn.IPtablesLogParser(ConfigData)

#-----make sure we're sorting in the correct way-----
iptables_log_parser.process_ip_log_view(max_age='no_limit', sort_by='date_ip')
#-----log the current time-----
start_time = time.time()
datetime_now = iptables_log_parser.util.current_datetime()
print(datetime_now)

#--------------------------------------------------------------------------------

process_filename = 'update-ip-log.py'
process_filepath = f'/opt/zzz/python/bin/{process_filename}'

if args.country or args.update or args.summary:
    if iptables_log_parser.util.check_db_maintenance_flag():
        db_maintenance_note = iptables_log_parser.util.get_db_maintenance_note()
        print(f'DB maintenance flag is set: {db_maintenance_note}\nexiting...')
        sys.exit()

#-----work on command-line options-----
if args.init:
    #-----usually only on install, or when upgrading to the version that has this feature-----
    iptables_log_parser.init_db()
if args.country:
    iptables_log_parser.util.set_db_maintenance_flag('update-ip-log: country')
    try:
        iptables_log_parser.update_country_codes()
    except:
        print('ERROR: update_country_codes() crashed')
    iptables_log_parser.util.clear_db_maintenance_flag()
if args.update:
    count_update = iptables_log_parser.util.count_running_processes(name=process_filename, cmdline=[process_filepath, '--update'])
    count_summary = iptables_log_parser.util.count_running_processes(name=process_filename, cmdline=[process_filepath, '--summary'])
    if count_update>1 or count_summary>0:
        print('ERROR: another update-ip-log process is running')
        sys.exit()
    #-----frequently, maybe every 4 minutes-----
    iptables_log_parser.util.set_db_maintenance_flag('update-ip-log: update')
    try:
        iptables_log_parser.parse_latest_logs_upsert(update_db=True)
    except:
        print('ERROR: parse_latest_logs_upsert() crashed')
    iptables_log_parser.util.clear_db_maintenance_flag()
if args.summary:
    count_summary = iptables_log_parser.util.count_running_processes(name=process_filename, cmdline=[process_filepath, '--summary'])
    if count_summary>1:
        print('ERROR: another update-ip-log SUMMARY process is running')
        sys.exit()
    #-----once a day-----
    iptables_log_parser.rebuild_summary_table()

#-----close cursor and DB when done using them-----
iptables_log_parser.db.db_disconnect()

runtime = time.time() - start_time
print(f'Runtime: {runtime} seconds')
print("Done")
