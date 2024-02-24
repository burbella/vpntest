#!/bin/bash
#-----run this after a server IP change to implement the changes in the Zzz system-----

echo "Updating Server IP in Zzz System"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid

echo "updating iptables"
/opt/zzz/python/bin/init-iptables.py

echo "updating BIND"
/opt/zzz/python/bin/build-config.py --bind
systemctl restart bind9

echo "updating openvpn"
/opt/zzz/python/bin/build-config.py --openvpn-client
/opt/zzz/python/bin/build-config.py --openvpn-server
/home/ubuntu/bin/openvpn-restart

echo "restarting apache"
systemctl restart apache2

echo "restarting zzz"
systemctl restart zzz

# this also restarts squid
echo "restarting squid/zzz_icap"
/home/ubuntu/bin/icap-restart
echo "DONE"

echo
echo "Follow INSTALL.txt Step 6 to re-install openvpn configs on client devices."
