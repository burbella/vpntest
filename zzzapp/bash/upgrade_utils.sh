#!/bin/bash
#-----shell script utility functions for use in upgrade scripts-----
# USAGE:
#   source $REPOS_DIR/zzzapp/bash/upgrade_utils.sh

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR

DB_FILE=/opt/zzz/sqlite/services.sqlite3
PYTHON_DIR=/opt/zzz/python

#LIVE
LOG_UPGRADE_OUTPUT=/opt/zzz/apache/dev/zzz-upgrade.log
#TEST
#LOG_UPGRADE_OUTPUT=/home/ubuntu/test/test-zzz-upgrade.log

#--------------------------------------------------------------------------------

log_header() {
    local SCRIPTNAME=`basename "$0"`
    echo "$SCRIPTNAME - START" >> $LOG_UPGRADE_OUTPUT
    echo "upgrading the Zzz system from version $1 to $2" >> $LOG_UPGRADE_OUTPUT
}

#--------------------------------------------------------------------------------

check_if_root() {
    #-----exit if not running as root-----
    if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root" >> $LOG_UPGRADE_OUTPUT
        exit 1
    fi
}

#--------------------------------------------------------------------------------

#-----integer test for both params, make sure it's a one-version difference-----
check_if_valid_version_numbers() {
    local CURRENT_VERSION=$1
    local NEW_VERSION=$2
    local ZZZ_VERSION_REGEX='^[0-9]+$'
    
    if [[ ${#CURRENT_VERSION} -gt 8 ]]; then
        echo "ERROR: CURRENT_VERSION too large, must be under 9 digits" >> $LOG_UPGRADE_OUTPUT
        exit 1
    fi
    
    if [[ ${#NEW_VERSION} -gt 8 ]]; then
        echo "ERROR: NEW_VERSION too large, must be under 9 digits" >> $LOG_UPGRADE_OUTPUT
        exit 1
    fi
    
    if [[ ! "$CURRENT_VERSION" =~ $ZZZ_VERSION_REGEX ]]; then
        echo "ERROR: invalid zzz_system upgrade CURRENT_VERSION number" >> $LOG_UPGRADE_OUTPUT
        exit 1
    fi
    
    if [[ ! "$NEW_VERSION" =~ $ZZZ_VERSION_REGEX ]]; then
        echo "ERROR: invalid zzz_system upgrade NEW_VERSION number" >> $LOG_UPGRADE_OUTPUT
        exit 1
    fi
    
    # query the installed version from the DB, check here
    ZZZ_VERSION=`sqlite3 $DB_FILE "select version from zzz_system"`
    if [[ $ZZZ_VERSION -ne $CURRENT_VERSION ]]; then
        echo "ERROR: CURRENT_VERSION '$CURRENT_VERSION' does not match zzz_system version '$ZZZ_VERSION'" >> $LOG_UPGRADE_OUTPUT
        exit 1
    fi
    
    EXPECTED_NEW_VERSION=$((CURRENT_VERSION+1))
    if [[ $NEW_VERSION -ne $EXPECTED_NEW_VERSION ]]; then
        echo "ERROR: NEW_VERSION '$NEW_VERSION' does not match the expected new version '$EXPECTED_NEW_VERSION'" >> $LOG_UPGRADE_OUTPUT
        exit 1
    fi
}

#--------------------------------------------------------------------------------

check_if_db_upgrade_file_exists() {
    DB_UPGRADE_FILEPATH=$REPOS_DIR/upgrade/db/$1
    if [[ -f "$DB_UPGRADE_FILEPATH" ]]; then
        echo "DB file exists: $DB_UPGRADE_FILEPATH" >> $LOG_UPGRADE_OUTPUT
    else
        echo "ERROR - DB file not found: $DB_UPGRADE_FILEPATH" >> $LOG_UPGRADE_OUTPUT
        exit 1
    fi
}

#--------------------------------------------------------------------------------

shutdown_common_apps() {
    #-----give the zzz daemon time to shut itself down-----
    sleep 3
    echo "Stopping apache and zzz services..." >> $LOG_UPGRADE_OUTPUT
    systemctl stop apache2 >> $LOG_UPGRADE_OUTPUT
    systemctl stop zzz >> $LOG_UPGRADE_OUTPUT
    systemctl stop zzz_icap >> $LOG_UPGRADE_OUTPUT
}

#--------------------------------------------------------------------------------

update_db() {
    local DB_UPGRADE_FILE=$1
    echo "Updating DB..." >> $LOG_UPGRADE_OUTPUT
    sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/$DB_UPGRADE_FILE >> $LOG_UPGRADE_OUTPUT
    echo "DONE" >> $LOG_UPGRADE_OUTPUT
}

update_db_version_only() {
    local CURRENT_VERSION=$1
    local NEW_VERSION=$2
    
    echo "Updating DB Version only..." >> $LOG_UPGRADE_OUTPUT
    sqlite3 $DB_FILE "update zzz_system set version=$NEW_VERSION, last_updated=datetime('now') where version=$CURRENT_VERSION" >> $LOG_UPGRADE_OUTPUT
    echo "DONE" >> $LOG_UPGRADE_OUTPUT
}

#--------------------------------------------------------------------------------

install_python_modules() {
    echo >> $LOG_UPGRADE_OUTPUT
    echo "Installing python modules..." >> $LOG_UPGRADE_OUTPUT
    /opt/zzz/python/bin/subprocess/zzz-app-update.sh >> $LOG_UPGRADE_OUTPUT
    echo "DONE" >> $LOG_UPGRADE_OUTPUT
}

#--------------------------------------------------------------------------------

startup_common_apps() {
    echo "Restarting apache and zzz services..." >> $LOG_UPGRADE_OUTPUT
    # restart is more reliable than start with apache2
    # sometimes start just fails for some reason
    systemctl restart apache2 >> $LOG_UPGRADE_OUTPUT
    systemctl start zzz >> $LOG_UPGRADE_OUTPUT
    systemctl start zzz_icap >> $LOG_UPGRADE_OUTPUT
}

#--------------------------------------------------------------------------------

log_footer() {
    local SCRIPTNAME=`basename "$0"`
    echo "$SCRIPTNAME - END" >> $LOG_UPGRADE_OUTPUT
}

#--------------------------------------------------------------------------------

#TODO: finish this
#-----run the common functions needed for a simple version upgrade-----
simple_upgrade() {
    local CURRENT_VERSION=$1
    local NEW_VERSION=$2
    
    log_header $CURRENT_VERSION $NEW_VERSION
    
    check_if_root
    #echo "This script must be run as root" >> $LOG_UPGRADE_OUTPUT
    
    check_if_valid_version_numbers $CURRENT_VERSION $NEW_VERSION
    
    #-----stop apps-----
    shutdown_common_apps
    
    #-----install zzz upgrades-----
    update_db_version_only $CURRENT_VERSION $NEW_VERSION
    
    install_python_modules
    
    #-----restart apps-----
    startup_common_apps
    
    log_footer
}

#TODO: finish this
#-----simple version upgrade, but with custom DB changes-----
simple_upgrade_custom_db() {
    local CURRENT_VERSION=$1
    local NEW_VERSION=$2
    
    #-----vars-----
    DB_STR1=db_
    DB_STR2=_
    DB_STR3=.sql
    #DB_UPGRADE_FILE=db_13_14.sql
    DB_UPGRADE_FILE="$DB_STR1$CURRENT_VERSION$DB_STR2$NEW_VERSION$DB_STR3"
    
    log_header $CURRENT_VERSION $NEW_VERSION
    
    check_if_root
    #echo "This script must be run as root" >> $LOG_UPGRADE_OUTPUT
    
    check_if_valid_version_numbers $CURRENT_VERSION $NEW_VERSION
    
    check_if_db_upgrade_file_exists $DB_UPGRADE_FILE
    
    #-----stop apps-----
    shutdown_common_apps
    
    #-----install zzz upgrades-----
    update_db $DB_UPGRADE_FILE
    
    install_python_modules
    
    #-----restart apps-----
    startup_common_apps
    
    log_footer
}

