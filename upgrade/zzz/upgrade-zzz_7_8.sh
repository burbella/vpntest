#!/bin/bash
#-----upgrade zzz system from version 7 to 8-----

echo "upgrade-zzz_7_8.sh - START"
echo "upgrading the Zzz system from version 7 to 8"

#-----exit if not running as root-----
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 
    exit 1
fi

REPOS_DIR=/home/ubuntu/repos/test
DB_FILE=/opt/zzz/sqlite/services.sqlite3

touch /etc/bind/settings/countries.conf
chown root.bind /etc/bind/settings/countries.conf
chmod 644 /etc/bind/settings/countries.conf

echo
echo "Updating DB..."
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_7_8.sql
echo "DONE"

echo
echo "Installing python modules..."
/opt/zzz/python/bin/subprocess/zzz-app-update.sh
echo "DONE"

echo "Restarting apache, BIND, and zzz services..."
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
systemctl restart bind9
systemctl restart zzz

echo
echo "upgrade-zzz_7_8.sh - END"
