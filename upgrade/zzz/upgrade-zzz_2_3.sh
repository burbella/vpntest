#!/bin/bash
#-----upgrade zzz system from version 2 to 3-----

echo "upgrade-zzz_2_3.sh - START"
echo "upgrading the Zzz system from version 2 to 3"

#-----exit if not running as root-----
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 
    exit 1
fi

REPOS_DIR=/home/ubuntu/repos/test
DB_FILE=/opt/zzz/sqlite/services.sqlite3

echo
echo "Stopping apache and zzz services..."
systemctl stop apache2
systemctl stop zzz

echo
echo "Updating DB..."
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_2_3.sql
echo "DONE"

echo
echo "Installing python modules..."
/opt/zzz/python/bin/subprocess/zzz-app-update.sh

echo
echo "Starting apache and zzz services..."
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
systemctl start zzz

echo
echo "upgrade-zzz_2_3.sh - END"
