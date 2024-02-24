#!/bin/bash
#-----upgrade zzz system from version 11 to 12-----
# accepted/blocked logs now go to one file instead of two

echo "upgrade-zzz_11_12.sh - START"
echo "upgrading the Zzz system from version 11 to 12"

#-----exit if not running as root-----
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 
    exit 1
fi

REPOS_DIR=/home/ubuntu/repos/test
DB_FILE=/opt/zzz/sqlite/services.sqlite3

#-----system file updates-----
for i in \
    /opt/zzz/apache/zzz_version_check.txt  ; do
    touch $i
    chown root.root $i
    chmod 644 $i
done

systemctl stop apache2
systemctl stop zzz
systemctl stop zzz_icap

echo "Updating DB..."
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_11_12.sql
echo "DONE"

echo
echo "Installing python modules..."
/opt/zzz/python/bin/subprocess/zzz-app-update.sh
echo "DONE"

echo "Restarting apache and zzz services..."
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
systemctl start zzz
systemctl start zzz_icap

echo
echo "upgrade-zzz_11_12.sh - END"
