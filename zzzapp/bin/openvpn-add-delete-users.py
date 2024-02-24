#!/opt/zzz/venv/bin/python3

#-----add and delete users for openvpn-----

import argparse
import site
import os
import sys

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.UserManager

#-----run at minimum priority-----
os.nice(19)

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('openvpn-add-delete-users', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if config.is_valid():
    print('zzz config is valid')
else:
    sys.exit('ERROR: invalid zzz config')

user_manager = zzzevpn.UserManager(ConfigData)

#--------------------------------------------------------------------------------

#-----read command-line options-----
arg_parser = argparse.ArgumentParser(description='Zzz script to manage openvpn users')
arg_parser.add_argument('--verify-users', dest='verify_users', action='store_true', help='check the config file for user list changes')
arg_parser.add_argument('--update-db', dest='update_db', action='store_true', help='write new users list to the DB')
args = arg_parser.parse_args()

if args.verify_users:
    user_manager.verify_users()
    user_manager.make_add_users_list()
    user_manager.make_delete_users_list()
    if args.update_db:
        user_manager.update_db_users_list()
