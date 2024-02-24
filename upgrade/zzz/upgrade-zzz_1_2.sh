#!/bin/bash
#-----upgrade zzz system from version 1 to 2-----

echo "upgrade-zzz_1_2.sh - START"

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
echo "updating DB..."
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_2.sql
echo "DONE"

echo
echo "Installing python modules..."

for i in \
    Config.py \
    SystemCommand.py \
    UpdateOS.py \
    UpdateZzz.py \
    Util.py; do
    cp $REPOS_DIR/zzzapp/lib/$i /opt/zzz/python/lib
done

echo
echo "Starting apache and zzz services..."
systemctl start apache2
systemctl start zzz

echo
echo "upgrade-zzz_1_2.sh - END"
