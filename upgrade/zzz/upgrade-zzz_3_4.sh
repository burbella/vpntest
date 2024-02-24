#!/bin/bash
#-----upgrade zzz system from version 3 to 4-----

echo "upgrade-zzz_3_4.sh - START"
echo "upgrading the Zzz system from version 3 to 4"

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
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_3_4.sql
echo "DONE"

echo
echo "Installing python modules..."
/opt/zzz/python/bin/subprocess/zzz-app-update.sh

#-----load countries into the country table-----
/opt/zzz/python/bin/init-country-table.py

echo
echo "Starting apache and zzz services..."
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
systemctl start zzz

echo
echo "upgrade-zzz_3_4.sh - END"
