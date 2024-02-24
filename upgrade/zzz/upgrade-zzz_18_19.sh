#!/bin/bash
#-----upgrade zzz system from version 18 to 19-----

CURRENT_VERSION=18
NEW_VERSION=19

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

#-----give the old zzz daemon a chance to shut down-----
sleep 3

#-----openvpn config update-----
for i in \
    server.conf \
    server-dns.conf \
    server-filtered.conf \
    server-squid.conf ; do
    cp $REPOS_DIR/config/openvpn/$i /etc/openvpn/server
done
/home/ubuntu/bin/openvpn-restart

#-----install the init.d file-----
cp $REPOS_DIR/config/ubuntu/zzz_icap_initd.sh /etc/init.d/zzz_icap

#-----run the init.d update command when init.d files change-----
systemctl daemon-reload

#-----do the standard upgrade process-----
simple_upgrade $CURRENT_VERSION $NEW_VERSION

#-----make the new IP-country DB table-----
IP_COUNTRY_DB_FILE=/opt/zzz/sqlite/ip-country.sqlite3
sqlite3 $IP_COUNTRY_DB_FILE < $REPOS_DIR/install/database_setup_ip_country.sql
chown www-data.www-data $IP_COUNTRY_DB_FILE

nice -n 19 /opt/zzz/python/bin/update-ip-country-db.py --init --update

#-----ipdeny config update-----
rm /etc/cron.monthly/zzz-ipdeny
CRON_WEEKLY_DIR=/etc/cron.weekly
cp $REPOS_DIR/config/cron/zzz-ipdeny $CRON_WEEKLY_DIR
chmod 755 $CRON_WEEKLY_DIR/zzz-ipdeny
dos2unix -q $CRON_WEEKLY_DIR/zzz-ipdeny
