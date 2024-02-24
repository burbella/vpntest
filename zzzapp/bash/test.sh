#!/bin/bash
# TEST shell commands

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root

zzzConfig_VPNserver=`/opt/zzz/python/bin/config-parse.py --var 'IPv4/VPNserver'`
echo "VPNserver: $zzzConfig_VPNserver"

autodetect_ipv4
echo "ZZZ_AUTODETECT_IPV4: $ZZZ_AUTODETECT_IPV4"

autodetect_ipv6
echo "ZZZ_AUTODETECT_IPV6: $ZZZ_AUTODETECT_IPV6"
