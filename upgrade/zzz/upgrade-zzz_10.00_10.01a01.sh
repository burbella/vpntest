#!/bin/bash
#-----upgrade zzz system from version 100.01 to 100.02a-----
# old versioning system: 1 --> 2 --> 3 ... --> 19
# new versioning system: 10.00 --> 10.01a01 --> 10.01a02 --> 10.01
# do a manual version upgrade first:
#   sudo sqlite3 /opt/zzz/sqlite/services.sqlite3 < /home/ubuntu/repos/test/upgrade/db/version_change.sql

CURRENT_VERSION=10.00
NEW_VERSION=10.01a01

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

#-----give the old zzz daemon a chance to shut down-----
sleep 3

#-----do the standard upgrade process-----
simple_upgrade $CURRENT_VERSION $NEW_VERSION
