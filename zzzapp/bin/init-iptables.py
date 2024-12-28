#!/opt/zzz/venv/bin/python3

#-----iptables - make rules to route traffic-----
# make_router_config() - the static rules file needs to be created at install time
#   it gets updated if the Settings checkbox changes for open-squid

import argparse
import os
import site
import sys

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz iptables init', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn

parser = argparse.ArgumentParser(description='init iptables')
parser.add_argument('--custom_config', dest='custom_config', action='store_true', help='enable custom config(/home/ubuntu/test/iptables_config/zzz.conf)')
parser.add_argument('--test', dest='test_mode', action='store_true', help='writes files to the test directory (/home/ubuntu/test/iptables_config)')
args = parser.parse_args()

#-----test mode - write files to the test directory-----
# live directory: /etc/iptables
# last codebase installed: /opt/zzz/config/iptables
# test directory: /home/ubuntu/test/iptables_config
# test command: /opt/zzz/python/bin/init-iptables.py --test --custom_config
config = None
ConfigData = None
if args.custom_config:
    # load from a custom config file
    config = zzzevpn.Config(skip_autoload=True, test_mode=True)
    ConfigData = config.get_config_data(config_file='/home/ubuntu/test/iptables_config/zzz.conf', test_mode=True)
else:
    #-----get Config-----
    config = zzzevpn.Config(skip_autoload=True)
    ConfigData = config.get_config_data()

if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

if args.test_mode:
    test_dir = '/home/ubuntu/test/iptables_config'
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    # all IPv4 files written in IPtables.py
    config_entries = ['router_config_dst', 'dst_filepath', 'dst_countries_filepath', 'dst_allowlist_filepath', 'dst_log_accepted_filepath']
    # modify the ConfigData entries to point to the test directory
    ConfigData['UpdateFile']['iptables']['router_config_dst'] = f'{test_dir}/iptables-zzz.conf'
    ConfigData['UpdateFile']['iptables']['dst_filepath'] = f'{test_dir}/ip-blacklist.conf'
    ConfigData['UpdateFile']['iptables']['dst_countries_filepath'] = f'{test_dir}/ip-countries.conf'
    ConfigData['UpdateFile']['iptables']['dst_allowlist_filepath'] = f'{test_dir}/ip-allowlist.conf'
    ConfigData['UpdateFile']['iptables']['dst_log_accepted_filepath'] = f'{test_dir}/ip-log-accepted.conf'
    ConfigData['UpdateFile']['iptables']['logrotate_dst'] = f'{test_dir}/logrotate-zzz-iptables'
    # print diffs for the user to review
    print('Diffs:')
    for entry in config_entries:
        print(f'diff {config.default_ConfigData["UpdateFile"]["iptables"][entry]} {ConfigData["UpdateFile"]["iptables"][entry]}')


iptables = zzzevpn.IPtables(ConfigData)

#--------------------------------------------------------------------------------

# self.ConfigData['UpdateFile']['iptables']['router_config_dst']
iptables.make_router_config()

iptables.make_iptables_allowlist()
iptables.make_iptables_denylist()
iptables.make_iptables_countries()
iptables.make_iptables_log_accept()
iptables.make_iptables_logrotate_config()

iptables.install_iptables_config()

#-----close cursor and DB when done using them-----
iptables.db.db_disconnect()

print("Done", flush=True)
