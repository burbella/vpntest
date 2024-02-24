#!/opt/zzz/venv/bin/python3

#TODO: finish this

#-----Squid Log processing-----
# this will be called a cron
# need to process squid logs frequently to keep DB table data recent for viewing
# keep a record of the time of the last line processed, so no duplicates are processed

import argparse
import os
import site
import sys

#-----run at minimum priority-----
os.nice(19)

#-----make sure we're running as root or exit-----
if os.geteuid()!=0:
    sys.exit('This script must be run as root!')

print('Zzz squid log processing', flush=True)

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.Config
# import zzzevpn.SquidLogParser

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

#-----read command-line options-----
arg_parser = argparse.ArgumentParser(description='Update Squid Logs in DB')
arg_parser.add_argument('-c', '--country', dest='country', action='store_true', help='update country codes in Squid logs')
arg_parser.add_argument('--max-rows', dest='max_rows', action='store', help='max rows to process')
arg_parser.add_argument('-u', '--update', dest='update', action='store_true', help='update the Squid Log DB')
args = arg_parser.parse_args()

action_count = 0
if args.country:
    action_count += 1
    print('  action: COUNTRY')
if args.update:
    action_count += 1
    print('  action: UPDATE')
if action_count > 1:
    print('ERROR: only one action allowed at a time (COUNTRY, UPDATE)')
    sys.exit()
if action_count == 0:
    arg_parser.print_help()
    sys.exit()

squid_log_parser = zzzevpn.SquidLogParser(ConfigData)

#-----make sure we're sorting in the correct way-----
# squid_log_parser.process_ip_log_view(max_age='no_limit', sort_by='date_ip')
#-----log the current time-----
datetime_now = squid_log_parser.util.current_datetime()
print(datetime_now)

#--------------------------------------------------------------------------------

process_filename = 'update-squid-log.py'
process_filepath = f'/opt/zzz/python/bin/{process_filename}'

#TODO: max lines when going live
#-----parse max allowed lines-----
# it seems to do about 2000 lines/sec
squid_log_parser.lines_to_analyze = 999999
# squid_log_parser.lines_to_analyze = 1000

if args.country or args.update:
    if squid_log_parser.util.check_db_maintenance_flag():
        db_maintenance_note = squid_log_parser.util.get_db_maintenance_note()
        print(f'DB maintenance flag is set: {db_maintenance_note}\nexiting...')
        sys.exit()

#-----work on command-line options-----
if args.country:
    squid_log_parser.util.set_db_maintenance_flag('update-squid-log: country')
    try:
        squid_log_parser.update_country_codes()
    except:
        print('ERROR: update_country_codes() crashed')
    squid_log_parser.util.clear_db_maintenance_flag()

if args.update:
    count_update = squid_log_parser.util.count_running_processes(name=process_filename, cmdline=[process_filepath, '--update'])
    if count_update>1:
        print('ERROR: another update-squid-log process is running')
        sys.exit()
    #-----frequently, maybe every 10 minutes-----
    # RDNS lookups have requests-per-second limits, so this needs to be done in a separate cron
    # squid_log_parser.use_cached_rdns(True)
    squid_log_parser.should_skip_rdns(True)
    squid_log_parser.util.set_db_maintenance_flag('update-squid-log: update')
    try:
        squid_log_parser.parse_latest_logs(update_db=True)
    except:
        print('ERROR: parse_latest_logs() crashed')
    squid_log_parser.util.clear_db_maintenance_flag()

#-----close cursor and DB when done using them-----
squid_log_parser.db.db_disconnect()

print("Done")
