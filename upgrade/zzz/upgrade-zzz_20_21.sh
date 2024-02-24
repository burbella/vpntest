#!/bin/bash
#-----upgrade zzz system from version 20 to 21-----

CURRENT_VERSION=20
NEW_VERSION=21

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

#-----give the old zzz daemon a chance to shut down-----
sleep 3

#-----new module to detect network interfaces-----
sudo -H pip3 install -q --force-reinstall --ignore-installed ifcfg
#-----new module to check process info-----
sudo -H pip3 install -q --force-reinstall --ignore-installed psutil

#-----do the standard upgrade process-----
simple_upgrade $CURRENT_VERSION $NEW_VERSION

#-----fix cron log dir permissions-----
chmod 755 /var/log/zzz/cron

#-----install fixed logrotate config for rsyslog-----
cp $REPOS_DIR/config/logrotated/zzz-iptables /etc/logrotate.d
dos2unix -q /etc/logrotate.d/zzz-iptables

#-----generate an iptables config that includes the correct network device name-----
/opt/zzz/python/bin/init-iptables-blacklist.py
