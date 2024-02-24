#!/bin/bash
#-----upgrade zzz system from version 5 to 6-----

echo "upgrade-zzz_5_6.sh - START"
echo "upgrading the Zzz system from version 5 to 6"

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
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_5_6.sql
echo "DONE"

echo
echo "Updating system files..."
ZZZ_ICAP_INITD_FILE=/etc/init.d/zzz_icap
cp $REPOS_DIR/config/ubuntu/zzz_icap_initd.sh $ZZZ_ICAP_INITD_FILE
dos2unix $ZZZ_ICAP_INITD_FILE
chmod 755 $ZZZ_ICAP_INITD_FILE
update-rc.d zzz_icap defaults
#TODO: run systemd enable?

SQUID_CONF=/etc/squid/squid.conf
cp $REPOS_DIR/config/squid/squid.conf $SQUID_CONF
dos2unix $SQUID_CONF
echo "DONE"

echo
echo "Installing python modules..."
/opt/zzz/python/bin/subprocess/zzz-app-update.sh
echo "DONE"

echo "Starting zzz_icap service..."
systemctl start zzz_icap
echo
echo "Restarting apache, squid, and zzz services..."
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
systemctl restart squid
systemctl start zzz

echo
echo "upgrade-zzz_5_6.sh - END"
