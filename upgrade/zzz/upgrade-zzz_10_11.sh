#!/bin/bash
#-----upgrade zzz system from version 10 to 11-----
# accepted/blocked logs now go to one file instead of two

echo "upgrade-zzz_10_11.sh - START"
echo "upgrading the Zzz system from version 10 to 11"

#-----exit if not running as root-----
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root" 
    exit 1
fi

REPOS_DIR=/home/ubuntu/repos/test
DB_FILE=/opt/zzz/sqlite/services.sqlite3

#-----system file updates-----
for i in \
    /var/log/iptables/ipv4.log \
    /var/log/iptables/ipv6.log  ; do
    touch $i
    chown syslog.syslog $i
    chmod 644 $i
done

#-----EasyRSA-----
# config\cron\zzz-re-issue-certs --> /etc/cron.d/
# config\easyrsa\vars-openvpn --> /home/ubuntu/easyrsa ?
# config\easyrsa\vars-squid --> /home/ubuntu/easyrsa ?

IPTABLES_LOGGING_CONF=/etc/rsyslog.d/11-iptables.conf
cp $REPOS_DIR/config/ubuntu/rsyslog-11-iptables.conf $IPTABLES_LOGGING_CONF
dos2unix $IPTABLES_LOGGING_CONF
systemctl restart rsyslog

echo "Updating DB..."
sqlite3 $DB_FILE < $REPOS_DIR/upgrade/db/db_10_11.sql
echo "DONE"

echo
echo "Installing python modules..."
/opt/zzz/python/bin/subprocess/zzz-app-update.sh
echo "DONE"

echo "Restarting apache, squid, and zzz services..."
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
systemctl restart zzz

echo
echo "upgrade-zzz_10_11.sh - END"
