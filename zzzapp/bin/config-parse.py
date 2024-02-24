#!/opt/zzz/venv/bin/python3

#-----parse zzz.conf data file, output data for bash scripts-----
# strings:
#   /opt/zzz/python/bin/config-parse.py --test
#   /opt/zzz/python/bin/config-parse.py --var 'LogParserRowLimit'
#   /opt/zzz/python/bin/config-parse.py --var 'PhysicalNetworkInterfaces/internal'
#   /opt/zzz/python/bin/config-parse.py --var 'IPv4/Log/all'
#
# YAML parse without Config.py:
#   /opt/zzz/python/bin/config-parse.py --var 'IPv4/VPNserver' --yaml
#
# array:
#   /opt/zzz/python/bin/config-parse.py --var 'ProtectedIPs'
#
# alternate config file, YAML parse without Config.py:
#   /opt/zzz/python/bin/config-parse.py --var 'IPv6/Activate' --config '/home/ubuntu/repos/test/config/zzz.conf' --yaml
#
# Config expects these files to be installed:
#   /etc/zzz.conf - user manually installs
#   /etc/hostname - built into linux
#   /opt/zzz/data/country-codes.json - installed by 040_install-zzz-tools.sh
#   /opt/zzz/data/TLD-list.txt - installed by zzz-app-update.sh
#   /opt/zzz/apache/dns-blacklist.txt - starts empty
#   /opt/zzz/apache/iptables-blacklist.txt - starts empty

import argparse
import site
import sys
import yaml

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

#--------------------------------------------------------------------------------

#-----recursive split on '/' for multi-level arrays-----
def get_var(ConfigData, args_var):
    items = args_var.split('/', maxsplit=1)
    if len(items)>1:
        requested_var = ConfigData.get(items[0], None)
        if requested_var:
            # only recurse if we found the next key
            return get_var(requested_var, items[1])
        else:
            return requested_var
    else:
        # no more levels to go down? return the data
        if isinstance(ConfigData, dict):
            requested_var = ConfigData.get(args_var, None)
            return requested_var
        else:
            return None

#--------------------------------------------------------------------------------

def load_file(config_filepath):
    conf_data_loaded = None
    with open(config_filepath, 'r') as conf_file:
        try:
            conf_data_loaded = yaml.safe_load(conf_file)
        except yaml.YAMLError as e:
            print("ERROR: config file parsing error")
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                print("Config file error position: line={}, column={}".format(mark.line+1, mark.column+1))
            return None
    return conf_data_loaded

#--------------------------------------------------------------------------------

def print_var(requested_var):
    if requested_var:
        if isinstance(requested_var, list):
            print('\n'.join(requested_var))
        else:
            print(requested_var)
    else:
        print('invalid_var')

#--------------------------------------------------------------------------------

#-----command-line args-----
parser = argparse.ArgumentParser(description='Zzz Config Parser')
parser.add_argument('--config', dest='config', action='store', help='parse a given YAML config file instead of the default file')
parser.add_argument('--test', dest='test', action='store_true', help='test the config file')
parser.add_argument('--var', dest='var', action='store', help='pull a var from the config')
parser.add_argument('--yaml', dest='yaml', action='store_true', help='parse YAML variables file without additional Config.py processing')
args = parser.parse_args()

#-----get default Config-----
config = zzzevpn.Config()
config_filepath = config.ConfigFile
if args.config:
    # parse a given YAML config file instead of the default file
    config_filepath = args.config

conf_data_loaded = None
# raw YAML parsing? Config.py is not involved, so no configtest here
if args.yaml:
    conf_data_loaded = load_file(config_filepath)
    if not conf_data_loaded:
        print('ERROR: config data loading failed, exiting')
        sys.exit(1)
    # parse YAML variables file without additional Config.py processing
    if args.var:
        requested_var = get_var(conf_data_loaded, args.var)
        print_var(requested_var)
    else:
        print('ERROR: no variable specified')
    sys.exit()

#-----reload if a custom config file is specified-----
if args.config:
    if config.ConfigFile != config_filepath:
        config = zzzevpn.Config(config_file=config_filepath, force_reload=True)
found_valid_config = config.is_valid()

# running a configtest? print a yes/no result
if args.test:
    if found_valid_config:
        print('valid')
    else:
        print('invalid')
    sys.exit()

# don't bother trying to continue if the config isn't valid
if not found_valid_config:
    print('ERROR: invalid config')
    sys.exit(1)

if args.var:
    ConfigData = getattr(config, 'ConfigData')
    requested_var = get_var(ConfigData, args.var)
    print_var(requested_var)
else:
    parser.print_help()

