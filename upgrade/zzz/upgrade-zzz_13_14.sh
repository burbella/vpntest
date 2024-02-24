#!/bin/bash
#-----upgrade zzz system from version 13 to 14-----

#-----EDIT THIS-----
CURRENT_VERSION=13
NEW_VERSION=14

#-----vars-----
DB_STR1=db_
DB_STR2=_
DB_STR3=.sql
#DB_UPGRADE_FILE=db_13_14.sql
DB_UPGRADE_FILE="$DB_STR1$CURRENT_VERSION$DB_STR2$NEW_VERSION$DB_STR3"
REPOS_DIR=/home/ubuntu/repos/test
LOG_UPGRADE_OUTPUT=/opt/zzz/apache/dev/zzz-upgrade.log

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

log_header $CURRENT_VERSION $NEW_VERSION

check_if_root

check_if_db_upgrade_file_exists $DB_UPGRADE_FILE

#-----stop apps-----
shutdown_common_apps

#-----install zzz upgrades-----
update_db $DB_UPGRADE_FILE

install_python_modules

#-----restart apps-----
startup_common_apps

log_footer
