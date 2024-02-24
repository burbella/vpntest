#!/opt/zzz/venv/bin/python3

#-----iptables - make rules to route traffic-----
# make_router_config() - the static rules file needs to be created at install time
#   it gets updated if the Settings checkbox changes for open-squid

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
# import zzzevpn.Config
# import zzzevpn.IPtables

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

iptables = zzzevpn.IPtables(ConfigData)

#--------------------------------------------------------------------------------

# self.ConfigData['UpdateFile']['iptables']['router_config_dst']
iptables.make_router_config()

iptables.make_iptables_allowlist()
iptables.make_iptables_denylist()
iptables.make_iptables_countries()
iptables.make_iptables_log_accept()

iptables.install_iptables_config()

#-----close cursor and DB when done using them-----
iptables.db.db_disconnect()

print("Done", flush=True)
