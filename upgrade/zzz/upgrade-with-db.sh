#!/bin/bash
#-----upgrade zzz system using version numbers specified on the command line, with a custom DB schema file-----

CURRENT_VERSION=$1
NEW_VERSION=$2

#-----don't proceed unless the config is OK-----
source /opt/zzz/util/util.sh
exit_if_configtest_invalid

#-----load upgrade utils-----
# REPOS_DIR is set by util.sh above
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
UPGRADE_UTILS_INSTALLED=/opt/zzz/upgrade/tmp/upgrade_utils.sh
cp -p $UPGRADE_UTILS $UPGRADE_UTILS_INSTALLED
dos2unix -q $UPGRADE_UTILS_INSTALLED
source $UPGRADE_UTILS_INSTALLED

#-----give the zzz daemon a chance to shut down-----
sleep 3

#-----full upgrade process, assumes a DB schema change file is in REPOS_DIR/upgrade/db-----
simple_upgrade_custom_db $CURRENT_VERSION $NEW_VERSION
