#!/bin/bash

#-----install custom logrotate configs-----

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: ZZZ_CONFIG_DIR

# /opt/zzz/python/bin/init-iptables.py generates /etc/logrotate.d/zzz-iptables from a template, so it is not installed from here

cp $ZZZ_CONFIG_DIR/logrotated/squid /etc/logrotate.d
cp $ZZZ_CONFIG_DIR/logrotated/zzz-logs /etc/logrotate.d
dos2unix -q /etc/logrotate.d/squid
dos2unix -q /etc/logrotate.d/zzz-logs

echo "$ZZZ_SCRIPTNAME - END"
