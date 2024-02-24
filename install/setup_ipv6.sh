#!/bin/bash
# setup_ipv6.sh
#
# optional IPv6 config
#
# 10/21/2019 - 7 countries without IPv6:
#   cf - Central African Republic
#   er - Eritrea
#   fk - Falkland Islands
#   kp - North Korea
#   ms - Montserrat
#   wf - Wallis and Futuna Islands
#   yt - Mayotte

echo "setup_ipv6.sh - START"

#-----import the config file parser-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_CONFIG_DIR

#--------------------------------------------------------------------------------

#-----get the server IP's if needed-----
zzzConfig_IPv6_VPNserver=`/opt/zzz/python/bin/config-parse.py --var 'IPv6/VPNserver'`
if [[ $zzzConfig_IPv6_VPNserver == "AUTODETECT" ]]; then
    autodetect_ipv6
    zzzConfig_IPv6_VPNserver=$ZZZ_AUTODETECT_IPV6
fi
echo "VPNserver IPv6: $zzzConfig_IPv6_VPNserver"

#TODO: finish this

#-----install BIND config-----
#TODO: process template file and install (template install IPv6 custom IP's)
# $ZZZ_CONFIG_DIR/named/named.conf.options.template --> /etc/bind/named.conf.options
#systemctl restart bind9

#-----register the local BIND server as a DNS service in dhclient-----
# start with the original OS file, then build on it
# requires a reboot to work
#cp /etc/dhcp/dhclient.conf.old /etc/dhcp/dhclient.conf
#echo -e "supersede domain-name-servers 127.0.0.1, 127.0.0.53, ::1;" >> /etc/dhcp/dhclient.conf
#dhclient

#-----install config files for the ip6tables scripts-----
# /etc/iptables:
#   ipset-ipv6-create-blacklist.sh --> ipset-ipv6-create-blacklist.conf
#   ipset-ipv6-create-countries.sh --> ipset-ipv6-create-countries.conf
#   ipset-ipv6-update-blacklist.sh --> ipset-ipv6-update-blacklist.conf
#   ipset-ipv6-update-countries.sh --> ipset-ipv6-update-countries.conf

#-----run the init script-----
# installs: BIND configs, openvpn configs, iptables configs
# based on: test/ipv6.py
#/opt/zzz/python/bin/ipv6-init.py

#--------------------------------------------------------------------------------

echo "setup_ipv6.sh - END"

