#!/bin/bash
#-----TEST upgrade script for the zzz system-----
# THIS DOES NOTHING, IT IS FOR TESTING ONLY

echo "upgrade-zzz_0_1.sh - START"
echo "THIS IS A TEST: upgrading the Zzz system (NO ACTUAL CHANGES)"

#-----exit if not running as root-----
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 
    exit 1
fi

REPOS_DIR=/home/ubuntu/repos/test
DB_FILE=/opt/zzz/sqlite/services.sqlite3

echo "Restarting apache and zzz services..."
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
systemctl restart zzz

echo
echo "upgrade-zzz_0_1.sh - END"
