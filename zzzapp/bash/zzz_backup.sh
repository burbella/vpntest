#!/bin/bash
#-----Zzz full system backup-----
# backups go here: /home/ubuntu/backup/

source /opt/zzz/util/util.sh

exit_if_not_running_as_root

lookup_zzz_db_version

DATETIME=`date '+%Y-%m-%d-%H-%M-%S'`

ZZZ_BACKUP_DIR=/home/ubuntu/backup
ZZZ_CUSTOM_DIR=backup-$ZZZ_VERSION-$DATETIME
ZZZ_BACKUP_FILE=$ZZZ_CUSTOM_DIR.tar.gz
#
ZZZ_BACKUP_CUSTOM_DIR=$ZZZ_BACKUP_DIR/$ZZZ_CUSTOM_DIR
ZZZ_BACKUP_FILEPATH=$ZZZ_BACKUP_DIR/$ZZZ_BACKUP_FILE
ZZZ_BACKUP_CHECKSUM=$ZZZ_BACKUP_FILEPATH.sha512

echo "Making backup directory: $ZZZ_BACKUP_CUSTOM_DIR"
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/config/bind/settings
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3/pki
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3/pki-openvpn-int
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3/pki-squid
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3/pki-squid-top
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/GeoIP
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/ipdeny-ipv4
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/ipdeny-ipv6
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/iptables/countries
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/openvpn/server
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/public_certs
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/sqlite
mkdir -p $ZZZ_BACKUP_CUSTOM_DIR/squid/ssl_cert

cd $ZZZ_BACKUP_DIR

#-----stop crons in case one of them want to write to the DB while it is copying-----
echo "Stopping cron"
systemctl stop cron

#-----stop services (zzz_icap will not go down as long as squid is running)-----
echo
echo "Stopping Services: apache2, squid, zzz, zzz_icap"
systemctl stop zzz
systemctl stop apache2
systemctl stop squid
systemctl stop squid-icap
systemctl stop zzz_icap

#-----give the zzz daemon a chance to shut down-----
sleep 3

#--------------------------------------------------------------------------------

echo
echo "Copying Files"

cp -p /etc/zzz.conf $ZZZ_BACKUP_CUSTOM_DIR/config

cp -pR /home/ubuntu/easyrsa3/pki $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3
cp -pR /home/ubuntu/easyrsa3/pki-openvpn-int $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3
cp -pR /home/ubuntu/easyrsa3/pki-squid $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3
cp -pR /home/ubuntu/easyrsa3/pki-squid-top $ZZZ_BACKUP_CUSTOM_DIR/easyrsa3

#-----BIND - only include Zzz custom files-----
# static files can be installed from repos
# server-specific files have to be re-built with whatever app builds them
# skip Zzz files with static or server-specific values:
#   named-settings.conf
#   named-zzz.conf
#   named.conf
#   named.conf.local
#   named.conf.options - has custom IPv6 IP's
#   null.zone.file
#   zzz.zzz.zone.file
for i in \
    dns-blacklist ; do
    cp -p /etc/bind/$i $ZZZ_BACKUP_CUSTOM_DIR/config/bind
done
cp -pR /etc/bind/settings $ZZZ_BACKUP_CUSTOM_DIR/config/bind

#-----only backup config files, not scripts or rules files-----
# skip Zzz files with static or server-specific values:
#   ip-blacklist-empty.conf
#   ip-blacklist-footer.conf
#   ip-blacklist.conf
#   ip-countries.conf
#   ip6-blacklist.conf
#   ip6-countries.conf
#   ip6tables-zzz.conf
#   iptables-zzz.conf
#   iptables.conf
for i in \
    ipset-update-allowlist.conf \
    ipset-update-blacklist.conf \
    ipset-update-countries.conf ; do
cp -p /etc/iptables/$i $ZZZ_BACKUP_CUSTOM_DIR/iptables
done

#-----squid-----
# skip Zzz files with static or server-specific values:
#   squid.conf
# not implemented yet: must-splice-sites.acl
for i in \
    nobumpsites.acl ; do
    cp -p /etc/squid/$i $ZZZ_BACKUP_CUSTOM_DIR/squid
done
cp -p /etc/squid/ssl_cert/* $ZZZ_BACKUP_CUSTOM_DIR/squid/ssl_cert

#-----only backup config files, not scripts or rules files-----
# skip Zzz files with static or server-specific values:
#   ipp-filtered.txt
#   server/*
# cp -pR /etc/openvpn/* $ZZZ_BACKUP_CUSTOM_DIR/openvpn
for i in \
    ca.crt \
    dh.pem \
    ta.key \
    vpn.zzz.zzz.crt \
    vpn.zzz.zzz.key \
    vpn.zzz.zzz_pem_pass.txt ; do
cp -p /etc/openvpn/$i $ZZZ_BACKUP_CUSTOM_DIR/openvpn
done

cp /opt/zzz/data/openvpn_users.txt $ZZZ_BACKUP_CUSTOM_DIR

#-----only back this up if we have it-----
MAXMIND_DB_FILE=/usr/share/GeoIP/GeoLite2-Country.mmdb
if [ -f $MAXMIND_DB_FILE ]; then
    cp -p $MAXMIND_DB_FILE $ZZZ_BACKUP_CUSTOM_DIR/GeoIP
fi

#TODO: FIND OTHER FILES MODIFIED DURING INSTALL

# useless log files? no need to backup?
# /opt/zzz/apache/dev/*
# /var/log/squid_access/access.log*

#TODO: maybe include GeoIP DB and ipdeny files? maybe make them optional?

#--------------------------------------------------------------------------------

#TODO: detect if the daemon is still running
#-----backup the DB-----
cp -p /opt/zzz/sqlite/services.sqlite3 $ZZZ_BACKUP_CUSTOM_DIR/sqlite
cp -p /opt/zzz/sqlite/country-IP.sqlite3 $ZZZ_BACKUP_CUSTOM_DIR/sqlite

#-----restart cron----- 
echo "restarting cron"
systemctl start cron

#-----restart services-----
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
echo
echo "Starting Services: apache2, squid, zzz, zzz_icap"
systemctl restart apache2
systemctl start zzz
systemctl start zzz_icap
systemctl start squid
systemctl start squid-icap

#--------------------------------------------------------------------------------

echo "Making tar.gz file: $ZZZ_BACKUP_FILEPATH"
# cd /home/ubuntu/test
# tar --gzip --create --file testzip.tar.gz testzip
# tar --gzip --list --file /home/ubuntu/test/testzip.tar.gz
tar --gzip --label=$ZZZ_CUSTOM_DIR --create --file $ZZZ_BACKUP_FILE $ZZZ_CUSTOM_DIR

#-----save the backup checksum-----
echo "Making checksum file: $ZZZ_BACKUP_CHECKSUM"
/usr/bin/sha512sum --binary $ZZZ_BACKUP_FILE > $ZZZ_BACKUP_CHECKSUM

#-----don't need the directory, now that it's archived in a .tar.gz-----
rm -rf $ZZZ_CUSTOM_DIR

#--------------------------------------------------------------------------------

