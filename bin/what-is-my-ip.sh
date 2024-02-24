#!/bin/bash
#-----lookup IPv4 and IPv6-----

#-----import the config file parser-----
source /opt/zzz/util/util.sh

autodetect_ipv4
echo "ipv4: $ZZZ_AUTODETECT_IPV4"

check_ipv6_activate
if [[ "$ZZZ_IPV6_ACTIVATE" == "True" ]]; then
    autodetect_ipv6
    echo "ipv6: $ZZZ_AUTODETECT_IPV6"
else
    echo "ipv6: not activated"
fi

#ifconfig eth0 | grep inet6 | grep -v 'inet6 fe80' | awk ' /'pattern'/ {print $2} '

