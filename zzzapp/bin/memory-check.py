#!/opt/zzz/venv/bin/python3

#-----check memory in use by various processes-----
# restart those processes if needed

import argparse
import os
import pprint
import site
import sys

#-----run at minimum priority-----
os.nice(19)

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz memory check', flush=True)
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
memory = zzzevpn.Memory(ConfigData)

#--------------------------------------------------------------------------------

def check_system_memory(memory: zzzevpn.Memory):
    mem_info = memory.check_system_memory()

    # system_memory = psutil.virtual_memory()
    print('-----')
    print('system memory:')
    pprint.pprint(mem_info['system_memory'])

    print(f'''total: {mem_info['total']}''')
    print(f'''free: {mem_info['free']}''')
    print(f'''used: {mem_info['used']}''')
    print(f'''avail: {mem_info['avail']}''')
    print('-----')

    return mem_info

#--------------------------------------------------------------------------------

def restart_bind(util: zzzevpn.Util):
    if os.geteuid()!=0:
        print('ERROR: This script must be run as root to do process restarts')
        return

    print('restarting BIND...')
    system_command = ['systemctl', 'restart', 'bind9']
    if util.run_script(system_command):
        print('BIND restarted')
    else:
        print('ERROR restarting BIND')

#--------------------------------------------------------------------------------

#TODO: check both squid and squid-icap
def restart_squid(util: zzzevpn.Util):
    if os.geteuid()!=0:
        print('ERROR: This script must be run as root to do process restarts')
        return

    print('restarting Squid...')
    system_command = ['/opt/zzz/python/bin/subprocess/squid-restart.sh']
    if util.run_script(system_command):
        print('Squid restarted')
    else:
        print('ERROR restarting Squid')

#--------------------------------------------------------------------------------

#-----read command-line options-----
arg_parser = argparse.ArgumentParser(description='Zzz script to check process memory usage and restart high-memory-usage processes')
arg_parser.add_argument('--all', dest='all', action='store_true', help='check all processes')
arg_parser.add_argument('--bind', dest='bind', action='store_true', help='check BIND')
arg_parser.add_argument('--restart', dest='restart', action='store_true', help='restart any processes over the memory limit')
arg_parser.add_argument('--squid', dest='squid', action='store_true', help='check Squid')
arg_parser.add_argument('--system', dest='system', action='store_true', help='check system memory')
args = arg_parser.parse_args()

all_memory_usage = memory.check_all_memory_usage()
should_check_bind = False
should_check_squid = False
should_restart = False

print('Date: ' + memory.util.current_datetime())

count_args = 0

if args.all:
    count_args += 1
    should_check_bind = True
    should_check_squid = True
    print('check memory usage for all monitored processes: bind, squid')

if args.bind:
    count_args += 1
    should_check_bind = True

if args.restart:
    count_args += 1
    should_restart = True

if args.squid:
    count_args += 1
    should_check_squid = True

if args.system:
    count_args += 1
    mem_info = check_system_memory(memory)

#--------------------------------------------------------------------------------

if should_check_bind:
    bind_usage = all_memory_usage['bind']
    expected_mem, restart_mem_usage, max_allowed = memory.estimate_memory_usage_bind()
    print('check if BIND is over its allowed memory limit')
    print(f'bind_usage={bind_usage}, restart_mem_usage={restart_mem_usage}')
    if bind_usage > restart_mem_usage:
        print('  BIND usage exceeds the restart limit')
        if should_restart:
            restart_bind(memory.util)
    else:
        print('  BIND memory usage is OK')

if should_check_squid:
    squid_usage = all_memory_usage['squid']
    max_allowed = ConfigData['MemoryUsage']['squid']['base_mem'] + ConfigData['MemoryUsage']['squid']['excess_allowed']
    print('check if Squid is over its allowed memory limit')
    print(f'squid_usage={squid_usage}, max_allowed={max_allowed}')
    if squid_usage > max_allowed:
        print('  Squid usage exceeds the restart limit')
        if should_restart:
            restart_squid(memory.util)
    else:
        print('  Squid memory usage is OK')

if count_args==0:
    arg_parser.print_help()
    sys.exit()

print("Done")
print('-'*80)
