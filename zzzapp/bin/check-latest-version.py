#!/opt/zzz/venv/bin/python3

#-----cron to check installed software versions daily-----
# note any updates in a file that apache can read

import argparse
import site
import os
import sys

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.CheckLatestVersion
# import zzzevpn.UpdateZzz

#-----run at minimum priority-----
os.nice(19)

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('CheckLatestVersion', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if config.is_valid():
    print('zzz config is valid')
else:
    sys.exit('ERROR: invalid zzz config')

settings = zzzevpn.Settings(ConfigData)
settings.get_settings()
# ConfigData=None, db=None, util=None, settings=None
check_latest_version = zzzevpn.CheckLatestVersion(ConfigData, settings.db, settings.util, settings)
update_zzz = zzzevpn.UpdateZzz(ConfigData, settings.db, settings.util, settings)

#--------------------------------------------------------------------------------

#-----command-line arg -i installs the code-----
parser = argparse.ArgumentParser(description='Zzz Version Checker')
parser.add_argument('-i', '--install', dest='install', action='store_true', help='force-install the latest version of the Zzz System')
parser.add_argument('-t', '--test', dest='test', action='store_true', help='do a test of the Zzz System installer')
args = parser.parse_args()

status = ''
if args.install:
    #-----set the force-install flag for Zzz System-----
    check_latest_version.install_zzz = True
    
    #-----testing mode for the installer-----
    if args.test:
        check_latest_version.test_install = True
        status = check_latest_version.queue_upgrade('upgrade-zzz_0_1.sh')
    else:
        status = update_zzz.request_zzz_update('queue_upgrades')
    check_latest_version.util.work_available(1)
elif settings.is_setting_enabled('check_zzz_update'):
    #-----only do version checks in cron if the Settings checkbox is checked-----
    status = update_zzz.request_zzz_update('version_checks_cron')
    check_latest_version.util.work_available(1)

print(status)
