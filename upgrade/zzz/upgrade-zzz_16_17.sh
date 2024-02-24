#!/bin/bash
#-----upgrade zzz system from version 16 to 17-----

CURRENT_VERSION=16
NEW_VERSION=17

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

#-----give the old zzz daemon a chance to shut down-----
sleep 3

mkdir -p /opt/zzz/upgrade

#-----get the subprocess script in place before running it-----
PYTHON_DIR=/opt/zzz/python
cp $REPOS_DIR/zzzapp/bin/subprocess/* $PYTHON_DIR/bin/subprocess
chmod 755 $PYTHON_DIR/bin/subprocess/*.sh
find $PYTHON_DIR -type f -exec dos2unix -q {} \;

# OLD daemon file:
#   zzzapp/bin/services_test.py
# NEW daemon file:
#   zzzapp/bin/services_zzz.py

simple_upgrade $CURRENT_VERSION $NEW_VERSION

#-----install non-IPv6 bind config-----
cp $REPOS_DIR/config/named/named.conf.options /etc/bind/
sudo systemctl reload bind9

#-----install squid config-----
cp $REPOS_DIR/config/squid/squid.conf /etc/squid/
dos2unix /etc/squid/squid.conf
sudo systemctl reload squid

#-----iptables initial DB init-----
/opt/zzz/python/bin/update-ip-log.py --init

#-----install iptables log processing crons-----
cp $REPOS_DIR/config/cron/zzz-update-ip-log /etc/cron.d/
dos2unix /etc/cron.d/zzz-update-ip-log

cp $REPOS_DIR/config/cron/zzz-update-ip-log-summary /etc/cron.daily/
dos2unix /etc/cron.daily/zzz-update-ip-log-summary
chmod 755 /etc/cron.daily/zzz-update-ip-log-summary

cp $REPOS_DIR/config/cron/zzz-ipdeny /etc/cron.monthly/
dos2unix /etc/cron.monthly/zzz-ipdeny
chmod 755 /etc/cron.monthly/zzz-ipdeny
