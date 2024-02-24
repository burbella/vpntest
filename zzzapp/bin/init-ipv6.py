#!/opt/zzz/venv/bin/python3

#TODO: this script will probably end up similar to init-iptables.py
#      the ipv6 init functions may be added to init-iptables.py, then this script can be removed

#-----initialize the IPv6 configs (at install time or later)-----
# based on test/ipv6.py
#   Reading File: REPOS_DIR/config/iptables/ip6tables-zzz.conf.template
#   Writing File: /etc/iptables/ip6tables-zzz.conf
#   Reading File: REPOS_DIR/config/named/named.conf.options.template
#   Writing File: /etc/bind/TEST-named.conf.options
#   Reading File: REPOS_DIR/config/named/zzz.zzz.zone.file.template
#   Writing File: /etc/bind/TEST-zzz.zzz.zone.file
#   Reading File: REPOS_DIR/config/openvpn/server.conf.template
#
# Example: IP64=2000:1111:2222:3333
#   openvpn_new: 2000:1111:2222:3333:10:8:0:1
#   openvpn_64: 2000:1111:2222:3333::/64
#   openvpn_subnet: 2000:1111:2222:3333:10:8::/96
#   Writing File: /etc/openvpn/server/TEST-server.conf
#   openvpn_64: 2000:1111:2222:3333::/64
#   openvpn_subnet: 2000:1111:2222:3333:10:6::/96
#   Writing File: /etc/openvpn/server/TEST-server-dns.conf
#   openvpn_64: 2000:1111:2222:3333::/64
#   openvpn_subnet: 2000:1111:2222:3333:10:7::/96
#   Writing File: /etc/openvpn/server/TEST-server-filtered.conf
#   openvpn_64: 2000:1111:2222:3333::/64
#   openvpn_subnet: 2000:1111:2222:3333:10:9::/96
#   Writing File: /etc/openvpn/server/TEST-server-ipv6-test.conf
#   openvpn_64: 2000:1111:2222:3333::/64
#   openvpn_subnet: 2000:1111:2222:3333:10:5::/96
#   Writing File: /etc/openvpn/server/TEST-server-squid.conf

import os
import site
import sys

#-----make sure we're running as root or exit-----
if os.geteuid()==0:
    print('Zzz DB init', flush=True)
else:
    sys.exit('This script must be run as root!')

#-----import modules from the lib directory-----
if sys.platform=='linux':
    site.addsitedir('/opt/zzz/python/lib')

import zzzevpn
# import zzzevpn.Config
# import zzzevpn.Settings

#-----get Config-----
config = zzzevpn.Config(skip_autoload=True)
ConfigData = config.get_config_data()
if not config.is_valid():
    sys.exit('ERROR: invalid zzz config file')

settings = zzzevpn.Settings(ConfigData)
settings.get_settings()

#TODO: finish loading data here
template_data = {
    'IPV6_IP6TABLES_5': '',
    'IPV6_IP6TABLES_6': '',
    'IPV6_IP6TABLES_7': '',
    'IPV6_IP6TABLES_8': '',
    'IPV6_IP6TABLES_9': '',
    'GOOGLE_DNS_1': '',
    'GOOGLE_DNS_2': '',
    'IPV6_IP6TABLES_SUBNET_64': '',
}

template_str = ''
src_filepath = ConfigData['UpdateFile']['bind_ipv6']['template_filepath']
dst_filepath = ConfigData['UpdateFile']['bind_ipv6']['dst_filepath']

#-----close cursor and DB when done using them-----
settings.db.db_disconnect()

print("Done", flush=True)
