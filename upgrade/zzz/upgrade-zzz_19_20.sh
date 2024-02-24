#!/bin/bash
#-----upgrade zzz system from version 19 to 20-----

CURRENT_VERSION=19
NEW_VERSION=20

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

#-----give the old zzz daemon a chance to shut down-----
sleep 3

#-----do the standard upgrade process-----
simple_upgrade_custom_db $CURRENT_VERSION $NEW_VERSION

#-----update cron files-----
mkdir -p /var/log/zzz/cron
ZZZ_CRON_INSTALLER=$REPOS_DIR/install/070_configure_cron.sh
chmod 755 $ZZZ_CRON_INSTALLER
dos2unix -q $ZZZ_CRON_INSTALLER
$ZZZ_CRON_INSTALLER --skip-ipdeny

#-----install new squid config, updated with the ICAP on/off according to Settings-----
/opt/zzz/python/bin/generate_squid_config.py

systemctl restart squid
