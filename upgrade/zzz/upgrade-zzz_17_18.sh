#!/bin/bash
#-----upgrade zzz system from version 17 to 18-----

CURRENT_VERSION=17
NEW_VERSION=18

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

#-----give the old zzz daemon a chance to shut down-----
sleep 3

sudo -H pip3 install -q --force-reinstall --ignore-installed python-magic

#-----apache config update-----
cp $REPOS_DIR/config/httpd/mpm_prefork.conf /etc/apache2/mods-available/

#-----install the init.d files-----
cp /home/ubuntu/repos/test/config/ubuntu/zzz_daemon_initd.sh /etc/init.d/zzz
cp /home/ubuntu/repos/test/config/ubuntu/zzz_icap_initd.sh /etc/init.d/zzz_icap

#-----run the init.d update command when init.d files change-----
systemctl daemon-reload

#-----do the standard upgrade process-----
simple_upgrade $CURRENT_VERSION $NEW_VERSION
