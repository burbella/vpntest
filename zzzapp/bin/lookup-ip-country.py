#!/opt/zzz/venv/bin/python3

#-----ip-country lookup by command line-----

import argparse
import os
import site
import sys

#-----make sure we're running as root or exit-----
if os.geteuid()!=0:
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

util = zzzevpn.Util(ConfigData)

#--------------------------------------------------------------------------------

#TEST:
# sudo /opt/zzz/python/bin/lookup-ip-country.py -q --ip=1.2.3.4

#-----read command-line options-----
arg_parser = argparse.ArgumentParser(description='IP-Country Lookup')
arg_parser.add_argument('--ip', dest='ip', action='store', help='IP to lookup')
arg_parser.add_argument('-q', dest='q', action='store_true', help='Quiet')
args = arg_parser.parse_args()

action_count = 0
if args.ip:
    action_count += 1
if action_count == 0:
    arg_parser.print_help()
    sys.exit()

if not args.q:
    print('Zzz IP-Country Lookup', flush=True)

if args.ip:
    if not args.q:
        print('Lookup up IP: ' + args.ip)
    country_found = util.lookup_ip_country(args.ip)
    if country_found:
        print(country_found)
else:
    print('ERROR: no IP specified')

if not args.q:
    print("Done", flush=True)
