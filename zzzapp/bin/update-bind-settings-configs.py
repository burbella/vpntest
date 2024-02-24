#!/opt/zzz/venv/bin/python3

#-----create settings config files for BIND based on settings text files-----

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
# import zzzevpn.BIND
# import zzzevpn.Config

print('Zzz BIND Settings config processing', flush=True)

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

bind = zzzevpn.BIND(ConfigData)
bind.update_bind_settings_files()

print("Done", flush=True)
