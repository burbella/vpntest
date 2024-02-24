#!/bin/bash
#-----upgrade zzz system from version 9 to 10-----
# IP log tables added
# ICAP server upgrade

echo "upgrade-zzz_9_10.sh - START"
echo "upgrading the Zzz system from version 9 to 10"

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

echo "Updating DB..."
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_9_10.sql
echo "DONE"

echo
echo "Installing python modules..."
/opt/zzz/python/bin/subprocess/zzz-app-update.sh
echo "DONE"

#-----zzz_icap gets stuck on restart if you don't stop squid first-----
echo "Stopping squid service..."
systemctl stop squid
echo
echo "Restarting zzz_icap service..."
systemctl restart zzz_icap
echo
echo "Restarting apache, squid, and zzz services..."
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
systemctl start squid
systemctl start zzz

echo
echo "upgrade-zzz_9_10.sh - END"
