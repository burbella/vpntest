#!/bin/bash

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

mkdir -p /etc/bind/settings
mkdir -p /etc/iptables/countries
mkdir -p /etc/openvpn/crls
mkdir -p /etc/openvpn/server
mkdir -p /etc/squid/ssl_cert

mkdir -p /opt/zzz/apache/dev
mkdir -p /opt/zzz/config
mkdir -p /opt/zzz/data/ipdeny-ipv4
mkdir -p /opt/zzz/data/ipdeny-ipv6
mkdir -p /opt/zzz/data/ssl-private
mkdir -p /opt/zzz/data/ssl-public
mkdir -p /opt/zzz/data/tldextract_cache
mkdir -p /opt/zzz/named/settings
mkdir -p /opt/zzz/python/.pytest_cache
mkdir -p /opt/zzz/python/bin/subprocess
mkdir -p /opt/zzz/python/lib/custom
mkdir -p /opt/zzz/python/lib/zzzevpn
mkdir -p /opt/zzz/python/templates
mkdir -p /opt/zzz/python/test/bin
mkdir -p /opt/zzz/python/test/html
mkdir -p /opt/zzz/python/test/install
mkdir -p /opt/zzz/python/test/lib
mkdir -p /opt/zzz/python/test/named
mkdir -p /opt/zzz/python/test/sqlite
mkdir -p /opt/zzz/python/test/templates
mkdir -p /opt/zzz/python/test/wsgi
mkdir -p /opt/zzz/sqlite
mkdir -p /opt/zzz/upgrade/db
mkdir -p /opt/zzz/upgrade/tmp
mkdir -p /opt/zzz/upgrade/zzz
mkdir -p /opt/zzz/util

mkdir -p /var/cache/squid
mkdir -p /var/cache/squid_icap
mkdir -p /var/lib/GeoIP
mkdir -p /var/log/iptables
mkdir -p /var/log/named
mkdir -p /var/log/squid_access
mkdir -p /var/log/zzz/cron
mkdir -p /var/log/zzz/icap

mkdir -p /var/www/.cache
mkdir -p /var/www/html/coverage
mkdir -p /var/www/html/img/custom
mkdir -p /var/www/wsgi

#-----same permissions as the PKI directory where these items are derived from-----
# squid needs to read the directory and read one file
chmod 755 /opt/zzz/data/ssl-private
chown root.root /opt/zzz/data/ssl-private
chmod 755 /opt/zzz/data/ssl-public
chown root.root /opt/zzz/data/ssl-public

chmod 755 /var/log/zzz/cron

#-----apache needs to write here-----
chmod 775 /opt/zzz/apache
chown root.www-data /opt/zzz/apache
chmod 755 /var/www/.cache
chown www-data.www-data /var/www/.cache

#-----ubuntu needs to write here to manage the venv directory-----
chmod 775 /opt/zzz
chown root.ubuntu /opt/zzz

#-----pytest runs as www-data-----
chown -R www-data.www-data /opt/zzz/python/test
chown www-data.www-data /var/www/html/coverage
chown www-data.www-data /opt/zzz/python/.pytest_cache

#-----icap runs as www-data-----
chmod 755 /var/log/zzz/icap
# chown www-data.www-data /var/log/zzz/icap

#-----tldextract pypi stores a TLD cache-----
chown www-data.www-data /opt/zzz/data/tldextract_cache
chmod 2775 /opt/zzz/data/tldextract_cache

echo "$ZZZ_SCRIPTNAME - END"
