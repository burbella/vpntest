#!/bin/bash
#-----upgrade zzz system from version 8 to 9-----

echo "upgrade-zzz_8_9.sh - START"
echo "upgrading the Zzz system from version 8 to 9"

#-----exit if not running as root-----
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 
    exit 1
fi

REPOS_DIR=/home/ubuntu/repos/test
DB_FILE=/opt/zzz/sqlite/services.sqlite3
CRON_DIR=/etc/cron.d
LOGROTATED_DIR=/etc/logrotate.d
IPTABLES_DIR=/etc/iptables

echo "Installing configs..."

mkdir -p /var/log/iptables
chmod 755 /var/log/iptables
for i in \
    /var/log/iptables/ipv4-accepted.log \
    /var/log/iptables/ipv4-blocked.log \
    /var/log/iptables/ipv6-accepted.log \
    /var/log/iptables/ipv6-blocked.log ; do
    touch $i
    chown syslog.syslog $i
    chmod 644 $i
done

IPTABLES_LOGGING_CONF=/etc/rsyslog.d/11-iptables.conf
cp $REPOS_DIR/config/ubuntu/rsyslog-11-iptables.conf $IPTABLES_LOGGING_CONF
dos2unix $IPTABLES_LOGGING_CONF

cp $REPOS_DIR/config/iptables/update_iptables.sh $IPTABLES_DIR
chmod 755 $IPTABLES_DIR/update_iptables.sh
dos2unix $IPTABLES_DIR/update_iptables.sh

cp $REPOS_DIR/config/logrotated/zzz-iptables $LOGROTATED_DIR
dos2unix $LOGROTATED_DIR/zzz-iptables

cp $REPOS_DIR/config/cron/zzz-logrotate-iptables $CRON_DIR
chmod 755 $CRON_DIR/zzz-logrotate-iptables
dos2unix $CRON_DIR/zzz-logrotate-iptables

echo "DONE"

echo
echo "Updating DB..."
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_8_9.sql
echo "DONE"

echo
echo "Installing python modules..."
/opt/zzz/python/bin/subprocess/zzz-app-update.sh
echo "DONE"

echo "Restarting apache, and zzz services..."
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
systemctl restart rsyslog
systemctl restart zzz

echo
echo "Updating iptables..."
/opt/zzz/python/bin/init-iptables-blacklist.py
/opt/zzz/python/bin/update-iptables-countries.py
echo "DONE"

echo
echo "upgrade-zzz_8_9.sh - END"
