#!/bin/bash
#-----upgrade zzz system from version 23 to 24-----

CURRENT_VERSION=23
NEW_VERSION=24

#-----don't proceed unless the config is OK-----
source /opt/zzz/util/util.sh
exit_if_configtest_invalid
# vars set in util.sh(version 23): REPOS_DIR

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
UPGRADE_UTILS_INSTALLED=/opt/zzz/upgrade/tmp/upgrade_utils.sh
cp -p $UPGRADE_UTILS $UPGRADE_UTILS_INSTALLED
dos2unix -q $UPGRADE_UTILS_INSTALLED
source $UPGRADE_UTILS_INSTALLED
UBUNTU_CONFIG_DIR=$REPOS_DIR/config/ubuntu

#-----give the zzz daemon a chance to shut down-----
sleep 3

#-----new dirs-----
mkdir -p /opt/zzz/data/ssl-public
chmod 700 /opt/zzz/data/ssl-public

mkdir -p /opt/zzz/python/test/bin
mkdir -p /opt/zzz/python/test/html
mkdir -p /opt/zzz/python/test/lib
mkdir -p /opt/zzz/python/test/sqlite
mkdir -p /opt/zzz/python/test/templates
mkdir -p /opt/zzz/python/test/wsgi
mkdir -p /opt/zzz/upgrade/db
mkdir -p /opt/zzz/upgrade/zzz
mkdir -p /var/log/zzz/icap
mkdir -p /var/www/html/coverage

#-----pytest runs as www-data-----
chown -R www-data.www-data /opt/zzz/python/test
chown -R www-data.www-data /var/www/html/coverage

#-----ICAP server runs as www-data-----
chmod 755 /var/log/zzz/icap
#chown www-data.www-data /var/log/zzz/icap

#-----second copy of squid connects to ICAP-----
mkdir -p /var/cache/squid_icap
chown proxy.proxy /var/cache/squid_icap
chmod 755 /var/cache/squid_icap

for i in \
    /var/log/zzz/icap/zzz-icap-data \    
    /opt/zzz/apache/dev/zzz-pytest.txt \
    /opt/zzz/apache/dev/zzz-upgrade.log ; do
    touch $i
    chmod 644 $i
done

#-----pip package changes-----
sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-tools.txt
sudo --user=ubuntu -H /opt/zzz/venv/bin/python3 -m pip install -r $REPOS_DIR/install/requirements.txt

#-----maxmind cron is back in use, install it-----
cp $REPOS_DIR/config/cron/zzz-maxmind /etc/cron.weekly
chmod 755 /etc/cron.weekly/zzz-maxmind
dos2unix -q /etc/cron.weekly/zzz-maxmind

#-----add apache2-dev-----
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install apache2-dev

#-----download/install mod_cspnonce-----
/opt/zzz/upgrade/get-mod_cspnonce.sh

#-----new apache modules-----
/usr/sbin/a2enmod expires cspnonce

#-----add redis server-----
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install redis-server

#-----do the standard upgrade process-----
simple_upgrade_custom_db $CURRENT_VERSION $NEW_VERSION

#-----make a second venv for testing-----
sudo --user=ubuntu /usr/bin/python3 -m venv /opt/zzz/venvtest
sudo --user=ubuntu -H /opt/zzz/venvtest/bin/pip3 install --upgrade pip
sudo --user=ubuntu -H /opt/zzz/venvtest/bin/python3 -m pip install -r $REPOS_DIR/install/requirements-tools.txt
sudo --user=ubuntu -H /opt/zzz/venvtest/bin/python3 -m pip install -r $REPOS_DIR/install/requirements.txt

#-----back to the first venv-----
source /opt/zzz/venv/bin/activate

#-----load the new util that just installed-----
source /opt/zzz/util/util.sh

cp $UBUNTU_CONFIG_DIR/.toprc /var/www
cp $UBUNTU_CONFIG_DIR/.vimrc /root
cp $UBUNTU_CONFIG_DIR/.vimrc /home/ubuntu

cp $REPOS_DIR/src/registrars.txt /opt/zzz/data
chmod 644 $DATA_DIR/registrars.txt
cp $REPOS_DIR/src/registrar_privacy_services.txt /opt/zzz/data
chmod 644 $DATA_DIR/registrar_privacy_services.txt

cp $REPOS_DIR/config/logrotated/squid /etc/logrotate.d
dos2unix -q /etc/logrotate.d/squid

cp $REPOS_DIR/config/cron/zzz-check-latest-version /etc/cron.daily
chmod 755 /etc/cron.daily/zzz-check-latest-version
dos2unix -q /etc/cron.daily/zzz-check-latest-version

cp $REPOS_DIR/config/cron/zzz-bind-restart /etc/cron.weekly
chmod 755 /etc/cron.weekly/zzz-bind-restart
dos2unix -q /etc/cron.weekly/zzz-bind-restart

cp $REPOS_DIR/config/cron/zzz-re-issue-certs /etc/cron.monthly
chmod 755 /etc/cron.monthly/zzz-re-issue-certs
dos2unix -q /etc/cron.monthly/zzz-re-issue-certs

#-----copy installer files out of repos and make them runnable-----
mkdir -p $ZZZ_INSTALLER_DIR
cp $REPOS_DIR/install/* $ZZZ_INSTALLER_DIR

#-----cleanup any line endings issues on installer files and make sure they can execute-----
find $ZZZ_INSTALLER_DIR -type f -exec dos2unix -q {} \;
chmod 755 $ZZZ_INSTALLER_DIR/*.sh

#--------------------------------------------------------------------------------

#-----redis server-----
systemctl stop redis
# config backup
cp -p /etc/redis/redis.conf /etc/redis/redis.conf.old
/opt/zzz/python/bin/build-config.py --redis
systemctl start redis

#-----new CRL for OpenVPN-----
/opt/zzz/util/build-crl-openvpn.sh

#-----squid updates-----
openssl dhparam -outform PEM -out /etc/squid/ssl_cert/dhparam.pem 2048
chown proxy.proxy /etc/squid/ssl_cert/dhparam.pem
chmod 640 /etc/squid/ssl_cert/dhparam.pem

#-----revoke existing squid CA under the root CA, then rebuild it under the openvpn CA-----
# this is similar to re-issue-cert-squid.sh, but references the root CA for this one-time upgrade
EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`
EASYRSA_VARS_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSAvars'`
VARS_DEFAULT_CA=$EASYRSA_VARS_DIR/$VARS_FILENAME_DEFAULT_CA

#-----rebuild easyrsa vars files-----
/opt/zzz/python/bin/build-config.py --easyrsa

#-----new VPN server-----
/opt/zzz/python/bin/build-config.py --openvpn-server
systemctl daemon-reload
systemctl enable openvpn-server@server-icap

cd $EASYRSA_DIR

#-----flush squid SSL cert cache-----
/home/ubuntu/bin/squid-clear-cert-cache no-restart

#-----revoke the old intermediate CA cert in the root CA-----
# this is the last time the root CA will be used for squid
./easyrsa --vars=$VARS_DEFAULT_CA revoke squid-int-ca

#TODO: manually run /opt/zzz/upgrade/replace_pki.sh

#-----Build a new PKI for the intermediate CA-----
/opt/zzz/util/init-squid-pki.sh
#-----rebuild squid.conf to include the cert chain file-----
/opt/zzz/python/bin/build-config.py --squid
#-----rebuild iptables for the new squid server-----
# init-iptables
# build-config: bind, openvpn-client, openvpn-server
# restart: bind, openvpn, squid, squid-icap, zzz_icap, zzz
/opt/zzz/util/update-server-networking.sh
#systemctl start squid

#-----separate squid daemon for ICAP-----
/lib/squid/security_file_certgen -c -s /var/cache/squid_icap/ssl_db -M 16MB
chown -R proxy.proxy /var/cache/squid_icap/ssl_db
squid -f /etc/squid/squid-icap.conf -z

#-----update the zzz init.d script-----
cp $UBUNTU_CONFIG_DIR/zzz_daemon_initd.sh /etc/init.d/zzz
dos2unix -q /etc/init.d/zzz
update-rc.d zzz defaults

#-----install ICAP init.d script, make the daemon auto-start on boot-----
#cp $UBUNTU_CONFIG_DIR/squid-icap-initd.sh /etc/init.d/squid-icap
SQUID_ICAP_FILE=/etc/init.d/squid-icap
cp -p /etc/init.d/squid $SQUID_ICAP_FILE
patch $SQUID_ICAP_FILE $REPOS_DIR/config/squid/squid-icap-initd.patch
chmod 755 $SQUID_ICAP_FILE
dos2unix -q $SQUID_ICAP_FILE
update-rc.d squid-icap defaults
systemctl daemon-reload

#-----make new apache cert chain file-----
/opt/zzz/util/output_minimal_cert_data.sh all
/opt/zzz/util/apache-rebuild-ca-fullchain.sh
/opt/zzz/python/bin/build-config.py --apache
systemctl restart apache2

#--------------------------------------------------------------------------------

#-----prep the squid gpg entries-----
# to be sure the download doesn't freeze, temporarily turn off the Settings checkbox "Apply Country-IP blocks to all VPN's"
wget --output-document=/home/ubuntu/src/squid-pgp.asc http://www.squid-cache.org/pgp.asc
$RUN_AS_UBUNTU gpg --homedir /home/ubuntu/.gnupg --import /home/ubuntu/src/squid-pgp.asc
$RUN_AS_UBUNTU gpg --homedir /home/ubuntu/.gnupg --keyserver keyserver.ubuntu.com --recv-keys B06884EDB779C89B044E64E3CD6DBF8EF3B17D3E

