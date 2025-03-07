#!/opt/zzz/venv/bin/python3

#-----iptables - make rules to route traffic-----

import argparse
import os
import pprint
import re
import site
import sys

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz iptables log analysis', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

arg_parser = argparse.ArgumentParser(description='iptables log analysis')
arg_parser.add_argument('--logfile', dest='logfile', action='store', help='logfile to analyze')
args = arg_parser.parse_args()

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

db = zzzevpn.DB(ConfigData)
db.db_connect(ConfigData['DBFilePath']['Services'])
util = zzzevpn.Util(ConfigData, db)
settings = zzzevpn.Settings(ConfigData, db, util)
settings.get_settings()

iptables = zzzevpn.IPtables(ConfigData, db, util, settings)
ip_log_raw_data = zzzevpn.IpLogRawData(ConfigData, db, util, settings)

#--------------------------------------------------------------------------------

# parse iptables log line
# regex_iptables_pattern = r'(?P<date>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6})'
regex_iptables_pattern = r'^(.+?) (\[.+?\]) ((.+?) \[(.+?)\]|(.+?))\s*$'
regex_iptables = re.compile(regex_iptables_pattern, re.DOTALL | re.MULTILINE)

count_args = 0
if args.logfile:
    count_args += 1
    if not util.file_is_accessible(args.logfile):
        sys.exit('ERROR: logfile is not accessible')

if count_args==0:
    arg_parser.print_help()
    sys.exit()


#--------------------------------------------------------------------------------

# grep LEN /opt/zzz/iptables/log/ipv4.log-1728246901 | less
# grep 192.81.245.126 /opt/zzz/iptables/log/ipv4.log-1728246901 | grep -P 'LEN\=26 '
# grep ICMP /var/log/iptables/* > ~/test/iptables_icmp_lines_2024-10-06.txt
# grep TCP /var/log/iptables/* | head -10
# grep UDP /var/log/iptables/* | head -10

# UDP EXAMPLE:
# /var/log/iptables/ipv4.log:2024-10-07T02:35:01.477337 [1589215.675090] zzz accepted IN=ens5 OUT=tun4 MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=1.2.3.4 DST=10.8.0.3 LEN=398 TOS=0x00 PREC=0x00 TTL=51 ID=59316 DF PROTO=UDP SPT=50030 DPT=57177 LEN=378 
# /var/log/iptables/ipv4.log:2024-10-07T02:35:01.481739 [1589215.680318] zzz accepted IN=ens5 OUT=tun4 MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=1.2.3.4 DST=10.8.0.3 LEN=178 TOS=0x00 PREC=0x00 TTL=51 ID=59318 DF PROTO=UDP SPT=50030 DPT=57177 LEN=158 
# /var/log/iptables/ipv4.log:2024-10-07T02:35:01.486600 [1589215.685083] zzz accepted IN=ens5 OUT=tun4 MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=1.2.3.4 DST=10.8.0.3 LEN=1196 TOS=0x00 PREC=0x00 TTL=51 ID=59322 DF PROTO=UDP SPT=50030 DPT=57177 LEN=1176 
# /var/log/iptables/ipv4.log:2024-10-07T02:35:01.504631 [1589215.703437] zzz accepted IN= OUT=ens5 SRC=172.30.3.23 DST=1.2.3.4 LEN=1248 TOS=0x00 PREC=0x00 TTL=64 ID=38278 DF PROTO=UDP SPT=39066 DPT=10648 LEN=1228 
# /var/log/iptables/ipv4.log:2024-10-07T02:35:01.511206 [1589215.710176] zzz accepted IN=ens5 OUT=tun4 MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=1.2.3.4 DST=10.8.0.3 LEN=1196 TOS=0x00 PREC=0x00 TTL=51 ID=59333 DF PROTO=UDP SPT=50030 DPT=57177 LEN=1176 

# TCP EXAMPLE:
# /var/log/iptables/ipv4.log:2024-10-07T02:35:01.472682 [1589215.671036] zzz accepted IN=ens5 OUT=tun4 MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=1.2.3.4 DST=10.8.0.3 LEN=1949 TOS=0x00 PREC=0x00 TTL=246 ID=641 PROTO=TCP SPT=443 DPT=62610 WINDOW=2603 RES=0x00 ACK PSH URGP=0 
# /var/log/iptables/ipv4.log:2024-10-07T02:35:01.571658 [1589215.770630] zzz accepted IN=ens5 OUT=tun4 MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=1.2.3.4 DST=10.8.0.3 LEN=3829 TOS=0x00 PREC=0x00 TTL=246 ID=643 PROTO=TCP SPT=443 DPT=62610 WINDOW=2603 RES=0x00 ACK PSH URGP=0 
# /var/log/iptables/ipv4.log:2024-10-07T02:35:01.630605 [1589215.828937] zzz accepted IN= OUT=lo SRC=127.0.0.1 DST=127.0.0.1 LEN=85 TOS=0x00 PREC=0x00 TTL=64 ID=50633 DF PROTO=TCP SPT=34534 DPT=29998 WINDOW=512 RES=0x00 ACK PSH URGP=0 

# ICMP EXAMPLE:
# ipv4.log-1728220561:2024-10-06T13:15:31.103142 [1541245.935271] zzz accepted IN=ens5 OUT=tun4 MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=1.2.3.4 DST=10.8.0.3 LEN=30 TOS=0x00 PREC=0x00 TTL=238 ID=16266 DF PROTO=ICMP TYPE=0 CODE=0 ID=1 SEQ=1759 
# ipv4.log-1728225361:2024-10-06T14:35:58.450988 [1546073.218762] zzz accepted IN=ens5 OUT= MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=172.30.3.1 DST=172.30.3.23 LEN=56 TOS=0x00 PREC=0x00 TTL=255 ID=0 DF PROTO=ICMP TYPE=3 CODE=4 [SRC=172.30.3.23 DST=1.2.3.4 LEN=1532 TOS=0x00 PREC=0x00 TTL=64 ID=44766 DF PROTO=UDP SPT=39066 DPT=10648 LEN=1512 ] MTU=1500 
# ipv4.log-1728231901:2024-10-06T16:24:12.159518 [1552566.842275] zzz accepted IN=ens5 OUT= MAC=01:02:03:04:05:06:07:08:09:0a:0b:0c:0d:0e SRC=1.2.3.4 DST=172.30.3.23 LEN=56 TOS=0x00 PREC=0x00 TTL=44 ID=14181 PROTO=ICMP TYPE=3 CODE=3 [SRC=172.30.3.23 DST=1.2.3.4 LEN=68 TOS=0x00 PREC=0x00 TTL=50 ID=44976 DF PROTO=UDP SPT=39066 DPT=57230 LEN=48 ] 

def print_var(var: str, varname: str, end_separator: bool=False):
    print(f'{varname}:')
    pprint.pprint(var)
    if end_separator:
        print('-'*80)
    else:
        print('*'*40)

def get_match_group(match: re.Match, group: int) -> str:
    try:
        return match.group(group)
    except IndexError:
        return None

def test_parse_line(line: str) -> dict:
    parsed_line = {}

    line = line.strip()
    if not line:
        return parsed_line

    line_parts = line.split(' ')
    print_var(line_parts, 'split line')

    match = regex_iptables.search(line)
    if match:
        log_timestamp = get_match_group(match, 1)
        log_pid = get_match_group(match, 2)
        log3 = get_match_group(match, 3)
        log4 = get_match_group(match, 4)
        log5 = get_match_group(match, 5)
        log6 = get_match_group(match, 6)
        log7 = get_match_group(match, 7)
        print_var(log_timestamp, 'log_timestamp')
        print_var(log_pid, 'log_pid')
        print_var(log3, 'log3')
        print_var(log4, 'log4')
        print_var(log5, 'log5')
        print_var(log6, 'log6')
        print_var(log7, 'log7', end_separator=True)

    return parsed_line

#--------------------------------------------------------------------------------

#-----default parsing function-----
ip_log_raw_data.parse_ip_log(args.logfile, extended_parsing=True)

# analyze each parameter found on each line of a given logfile, note any duplicate parameters
lines_parsed = 0
max_lines = 10
with open(args.logfile, 'r') as read_file:
    for line in read_file:
        parsed_line = test_parse_line(line)
        if not line:
            parsed_line
        lines_parsed += 1
        if lines_parsed >= max_lines:
            break


#--------------------------------------------------------------------------------

db.db_disconnect()

print("Done", flush=True)
