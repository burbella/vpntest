#!/bin/bash

# install appropriate config files: httpd.conf, ssl.conf
# restart with new configs

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_CONFIG_DIR

APACHE_CONF_DIR=/etc/apache2
REPOS_APACHE_DIR=$ZZZ_CONFIG_DIR/httpd

zzzConfig_Domain=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/Domain'`
echo "Apache ServerName: $zzzConfig_Domain"

#-----Backup the Ubuntu default apache configs-----
cp -p $APACHE_CONF_DIR/ports.conf $APACHE_CONF_DIR/ports.conf.orig

#-----disable apache's default site-----
#rm $APACHE_CONF_DIR/sites-enabled/000-default.conf
/usr/sbin/a2dissite 000-default

#-----install port listener config-----
cp $REPOS_APACHE_DIR/ports.conf $APACHE_CONF_DIR

#-----install process limiter-----
cp $ZZZ_CONFIG_DIR/httpd/mpm_event.conf $APACHE_CONF_DIR/mods-available

#-----download/install mod_cspnonce-----
/opt/zzz/upgrade/get-mod_cspnonce.sh

#-----install mod configs, enable mods needed-----
/usr/sbin/a2enmod headers cspnonce expires rewrite socache_shmcb ssl
# HTTP/2.0 support:
/usr/sbin/a2enmod setenvif mpm_event http2

#-----rebuild the apache config-----
/opt/zzz/python/bin/build-config.py --apache

#-----install/enable site configs-----
/usr/sbin/a2ensite zzz-site-http zzz-site-https

#-----download jquery-----
/opt/zzz/upgrade/get-jquery.sh

#-----custom favicon-----
/opt/zzz/python/bin/build-favicon.py

#-----restart apache to make the new configs load-----
systemctl restart apache2

echo "$ZZZ_SCRIPTNAME - END"
