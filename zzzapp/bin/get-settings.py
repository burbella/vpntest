#!/opt/zzz/venv/bin/python3

#-----get data from Settings, output data for bash scripts-----
# strings:
#   /opt/zzz/python/bin/config-parse.py --test
#   /opt/zzz/python/bin/config-parse.py --var 'LogParserRowLimit'
#   /opt/zzz/python/bin/config-parse.py --var 'PhysicalNetworkInterfaces/internal'
#   /opt/zzz/python/bin/config-parse.py --var 'IPv4/Log/all'
#
# array:
#   /opt/zzz/python/bin/config-parse.py --var 'ProtectedIPs'

import argparse
import os
import site
import sys

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#-----make sure we're running as root or exit-----
if os.geteuid()!=0:
    sys.exit('This script must be run as root!')

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config')

settings = zzzevpn.Settings(ConfigData)
settings.should_print_log(False)
settings.get_settings()

#--------------------------------------------------------------------------------

def get_var(settings: zzzevpn.Settings, args_var: str, print_var: bool=False):
    # checkboxes will be returned as TRUE/FALSE
    if args_var in settings.checkboxes_available:
        if settings.is_setting_enabled(args_var):
            if print_var:
                print('True')
            return True
        else:
            if print_var:
                print('False')
            return False

    requested_var = settings.SettingsData.get(args_var, None)
    if print_var:
        print(requested_var)
    return requested_var

#--------------------------------------------------------------------------------

#-----command-line args-----
parser = argparse.ArgumentParser(description='Get Settings')
parser.add_argument('--var', dest='var', action='store', help='pull a var from the Settings DB')
args = parser.parse_args()

if args.var:
    requested_var = get_var(settings, args.var, print_var=True)
else:
    parser.print_help()

