#!/opt/zzz/venv/bin/python3

#-----check diskspace in use-----
# clear old data from database to keep it under a set max diskspace limit
# /opt/zzz/python/bin/disk-check.py --all --flush-data

import argparse
import os
import pprint
import site
import sys
import time

#-----run at minimum priority-----
os.nice(19)

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz disk check', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')
disk = zzzevpn.Disk(ConfigData)

#--------------------------------------------------------------------------------

def check_db(args: argparse.Namespace, disk: zzzevpn.Disk):
    print('Check DB')
    flush_data = False
    if args.flush_data:
        flush_data = True
    
    disk.check_db(flush_data=flush_data)

#--------------------------------------------------------------------------------

def check_all(args: argparse.Namespace, disk: zzzevpn.Disk):
    print('Check all files')
    check_db(args, disk)

#--------------------------------------------------------------------------------

#-----read command-line options-----
arg_parser = argparse.ArgumentParser(description='Zzz script to disk usage and clear old data to free diskspace')
arg_parser.add_argument('--all', dest='all', action='store_true', help='check all files')
arg_parser.add_argument('--db', dest='db', action='store_true', help='check database')
arg_parser.add_argument('--delay', dest='delay', action='store', help='seconds to delay processing after startup, so other daily crons can go first')
arg_parser.add_argument('--flush-data', dest='flush_data', action='store_true', help='flush excess data')
args = arg_parser.parse_args()

print('Date: ' + disk.util.current_datetime())

count_args = 0

if args.delay:
    sleep_time = disk.util.get_int_safe(args.delay)
    if sleep_time:
        # max 15 minutes delay
        if sleep_time > 900:
            sleep_time = 900
        print(f'startup delay {sleep_time} seconds')
        time.sleep(sleep_time)

#NOTE: delay and flush_data don't count
if args.all:
    count_args += 1
    check_all(args, disk)
elif args.db:
    count_args += 1
    check_db(args, disk)

if count_args==0:
    arg_parser.print_help()
    sys.exit()

print("Done")
print('-'*80)
