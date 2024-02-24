#!/opt/zzz/venv/bin/python3

#-----ipset processing by command line-----
# make all ipset country lists once on install or when country lists are updated
# check for protected IP's and auto-exclude them
# pre-generate a default list and store in repos for install?


import os
import site
import sys

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz ipset processing', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.Config
# import zzzevpn.IPset

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

ipset = zzzevpn.IPset(ConfigData)

#--------------------------------------------------------------------------------

#-----read command-line options-----
#TODO: review if this is needed

ipset.update_country_lists()
ipset.install_country_lists()

#-----close cursor and DB when done using them-----
#ipset.db.db_disconnect()

print("Done", flush=True)
