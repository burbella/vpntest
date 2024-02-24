#!/bin/bash
#-----upgrade zzz system from version 15 to 16-----

#-----EDIT THIS-----
CURRENT_VERSION=15
NEW_VERSION=16

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

#-----install updated crons-----
# /config/cron/zzz-check-latest-version
# /config/cron/zzz-disk-cleanup
# /config/cron/zzz-ipdeny
CRON_DAILY_DIR=/etc/cron.daily
CRON_WEEKLY_DIR=/etc/cron.weekly
CRON_MONTHLY_DIR=/etc/cron.monthly

cp $REPOS_DIR/config/cron/zzz-check-latest-version $CRON_DAILY_DIR
chmod 755 $CRON_DAILY_DIR/zzz-check-latest-version
dos2unix $CRON_DAILY_DIR/zzz-check-latest-version

cp $REPOS_DIR/config/cron/zzz-disk-cleanup $CRON_WEEKLY_DIR
chmod 755 $CRON_WEEKLY_DIR/zzz-disk-cleanup
dos2unix $CRON_WEEKLY_DIR/zzz-disk-cleanup

cp $REPOS_DIR/config/cron/zzz-ipdeny $CRON_MONTHLY_DIR
chmod 755 $CRON_MONTHLY_DIR/zzz-ipdeny
dos2unix $CRON_MONTHLY_DIR/zzz-ipdeny

#-----re-issue apache certs monthly-----
cp $REPOS_DIR/config/cron/zzz-re-issue-certs $CRON_MONTHLY_DIR
chmod 755 $CRON_MONTHLY_DIR/zzz-re-issue-certs
dos2unix $CRON_MONTHLY_DIR/zzz-re-issue-certs

#-----new EasyRSA configs-----
cp $REPOS_DIR/config/easyrsa/vars-openvpn /home/ubuntu/easyrsa3
cp $REPOS_DIR/config/easyrsa/vars-squid /home/ubuntu/easyrsa3
dos2unix /home/ubuntu/easyrsa3/vars*

#-----the custom maxmind cron is no longer needed, there is a default in /etc/cron.d-----
rm /etc/cron.monthly/zzz-maxmind

#-----add the maxmind PPA for getting geoipupdate with apt-get-----
add-apt-repository -y ppa:maxmind/ppa
apt-get -q update

#-----install the latest version of geoipupdate-----
# backup the old config, manually transfer license info if needed
# force the new config file format here (but not in the 010_install-apps-from-repos.sh)
TODAY_YYYYMMDD=`date '+%Y%m%d'`
cp -p /etc/GeoIP.conf /etc/GeoIP.conf.$TODAY_YYYYMMDD
for i in \
    geoipupdate \
    libmaxminddb-dev \
    libmaxminddb0 ; do
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::="--force-confnew" install $i
done

simple_upgrade $CURRENT_VERSION $NEW_VERSION

#-----squid needs a new intermediate CA-----
cp $REPOS_DIR/zzzapp/bash/init-squid-pki.sh /opt/zzz/util
chmod 755 /opt/zzz/util/init-squid-pki.sh
dos2unix /opt/zzz/util/init-squid-pki.sh

#-----upgrade EasyRSA to 3.0.7 (this will be run manually, for safety)-----
#/opt/zzz/util/upgrade-easyrsa.sh

#-----run the cert re-issue scripts now (this will be run manually, for safety)-----
#/opt/zzz/util/re-issue-cert-apache.sh
#/home/ubuntu/bin/squid-clear-cert-cache no-restart
#/opt/zzz/util/init-squid-pki.sh
#systemctl start squid

