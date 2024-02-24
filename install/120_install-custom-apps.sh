#!/bin/bash

# make app and data directories
# install python apps
# make python apps executable

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_CONFIG_DIR

DATA_DIR=/opt/zzz/data
HTML_DIR=/var/www/html
WSGI_DIR=/var/www/wsgi
PYTHON_DIR=/opt/zzz/python
UTIL_DIR=/opt/zzz/util

#-----redis server-----
systemctl stop redis
# config backup
cp -p /etc/redis/redis.conf /etc/redis/redis.conf.old
/opt/zzz/python/bin/build-config.py --redis
systemctl start redis

#-----top command formatting in browser-----
cp $ZZZ_CONFIG_DIR/ubuntu/.toprc /var/www

#-----install init.d script, make the daemon auto-start on boot-----
cp $ZZZ_CONFIG_DIR/ubuntu/zzz_daemon_initd.sh /etc/init.d/zzz
chmod 755 /etc/init.d/zzz
dos2unix -q /etc/init.d/zzz
update-rc.d zzz defaults

#-----install ICAP init.d script, make the ICAP daemon auto-start on boot-----
cp $ZZZ_CONFIG_DIR/ubuntu/zzz_icap_initd.sh /etc/init.d/zzz_icap
chmod 755 /etc/init.d/zzz_icap
dos2unix -q /etc/init.d/zzz_icap
update-rc.d zzz_icap defaults

#-----run-on-boot service-----
cp $ZZZ_CONFIG_DIR/ubuntu/zzz-run-on-boot.service /etc/systemd/system
systemctl daemon-reload
systemctl enable zzz-run-on-boot.service

#-----install the GeoIP config file-----
# this only works if you make an account with maxmind.com and set EnableMaxMind=True in zzz.conf
# it will auto-download the DB file using their geoipupdate utility
cp $ZZZ_CONFIG_DIR/GeoIP.conf /etc/

#-----startup the daemons-----
systemctl start zzz
systemctl start zzz_icap

#-----restart apache to load the codebase-----
systemctl restart apache2

echo "$ZZZ_SCRIPTNAME - END"
