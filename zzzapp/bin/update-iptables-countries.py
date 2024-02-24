#!/opt/zzz/venv/bin/python3

#-----iptables processing by command line-----
# make all iptables country entries when settings are updated
# this should only be needed for testing, the daemon will do this automatically


import os
import site
import sys

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz iptables processing', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.Config
# import zzzevpn.IPtables

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

iptables = zzzevpn.IPtables(ConfigData)

#--------------------------------------------------------------------------------

#-----read command-line options-----
#TODO: review if this is needed

iptables.make_iptables_countries()
iptables.install_iptables_config()

#-----close cursor and DB when done using them-----
#ipset.db.db_disconnect()

print("Done", flush=True)
