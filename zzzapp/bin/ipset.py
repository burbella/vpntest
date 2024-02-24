#!/opt/zzz/venv/bin/python3

# OLD: !/usr/bin/env python3

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
# import zzzevpn.IPtables

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

#TODO: pass in DB and Util?
ipset = zzzevpn.IPset(ConfigData)
iptables = zzzevpn.IPtables(ConfigData, ipset.db, ipset.util)

#TEST
sys.exit('TEST: unfinished script, exiting early...')

#--------------------------------------------------------------------------------

#-----read command-line options-----
#TODO: finish this

#TEST
ipset.update_blacklist()
iptables.make_iptables_denylist()

#-----close cursor and DB when done using them-----
#service_request.db.db_disconnect()

print("Done", flush=True)
