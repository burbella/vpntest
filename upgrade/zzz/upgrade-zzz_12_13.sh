#!/bin/bash
#-----upgrade zzz system from version 12 to 13-----
# accepted/blocked logs now go to one file instead of two

LOG_UPGRADE_OUTPUT=/opt/zzz/apache/dev/zzz-upgrade.log

echo "upgrade-zzz_12_13.sh - START" >> $LOG_UPGRADE_OUTPUT
echo "upgrading the Zzz system from version 12 to 13" >> $LOG_UPGRADE_OUTPUT

#-----exit if not running as root-----
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" >> $LOG_UPGRADE_OUTPUT
    exit 1
fi

REPOS_DIR=/home/ubuntu/repos/test
DB_FILE=/opt/zzz/sqlite/services.sqlite3

#-----give the zzz daemon time to shut itself down-----
sleep 3

systemctl stop apache2 >> $LOG_UPGRADE_OUTPUT
systemctl stop zzz >> $LOG_UPGRADE_OUTPUT
systemctl stop zzz_icap >> $LOG_UPGRADE_OUTPUT

echo "Updating DB..." >> $LOG_UPGRADE_OUTPUT
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_12_13.sql >> $LOG_UPGRADE_OUTPUT
echo "DONE" >> $LOG_UPGRADE_OUTPUT

echo >> $LOG_UPGRADE_OUTPUT
echo "Installing python modules..." >> $LOG_UPGRADE_OUTPUT
/opt/zzz/python/bin/subprocess/zzz-app-update.sh >> $LOG_UPGRADE_OUTPUT
echo "DONE" >> $LOG_UPGRADE_OUTPUT

echo "Restarting apache and zzz services..." >> $LOG_UPGRADE_OUTPUT
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2 >> $LOG_UPGRADE_OUTPUT
systemctl start zzz >> $LOG_UPGRADE_OUTPUT
systemctl start zzz_icap >> $LOG_UPGRADE_OUTPUT

echo >> $LOG_UPGRADE_OUTPUT
echo "upgrade-zzz_12_13.sh - END" >> $LOG_UPGRADE_OUTPUT
