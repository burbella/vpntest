#!/bin/bash
#-----upgrade zzz system from version 21 to 22-----

CURRENT_VERSION=21
NEW_VERSION=22

#-----vars-----
REPOS_DIR=/home/ubuntu/repos/test

#-----load upgrade utils-----
UPGRADE_UTILS=$REPOS_DIR/zzzapp/bash/upgrade_utils.sh
dos2unix -q $UPGRADE_UTILS
source $UPGRADE_UTILS

#-----give the old zzz daemon a chance to shut down-----
sleep 3

#--------------------------------------------------------------------------------

#-----import the config file parser-----
ZZZ_CONFIG_FILE=/etc/zzz.conf
source /opt/zzz/util/util.sh
eval $(parse_yaml $ZZZ_CONFIG_FILE "zzzConfig_")

sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install wireguard

#-----new package to do HTTP requests-----
sudo -H pip3 install -q --force-reinstall --ignore-installed requests

#-----new package to do CIDR merges-----
sudo -H pip3 install -q --force-reinstall --ignore-installed netaddr

#-----nslookup package-----
sudo -H pip3 install -q --force-reinstall --ignore-installed nslookup

#-----need a backup directory-----
mkdir -p /home/ubuntu/backup
chmod ubuntu.ubuntu /home/ubuntu/backup

#-----apache - enable HTTP/2.0, fix crash on boot if apache loads before openvpn-----
/usr/sbin/a2enmod setenvif mpm_event http2
REPOS_APACHE_DIR=$REPOS_DIR/config/httpd
APACHE_CONF_DIR=/etc/apache2
cp $REPOS_APACHE_DIR/ports.conf $APACHE_CONF_DIR
cp $REPOS_DIR/config/httpd/mpm_event.conf $APACHE_CONF_DIR/mods-available
cp $REPOS_APACHE_DIR/zzz-site-http.conf $APACHE_CONF_DIR/sites-available
cp $REPOS_APACHE_DIR/zzz-site-https.conf $APACHE_CONF_DIR/sites-available

#-----BIND settings-----
/opt/zzz/python/bin/update-bind-settings-configs.py

#-----customize domain from config-----
perl -pi -e "s/services.zzz.zzz/$zzzConfig_Domain/g" $APACHE_CONF_DIR/sites-available/zzz-site-http.conf
perl -pi -e "s/services.zzz.zzz/$zzzConfig_Domain/g" $APACHE_CONF_DIR/sites-available/zzz-site-https.conf

#-----js/util/upgrade scripts - install the installer before calling simple_upgrade_custom_db-----
cp $REPOS_DIR/zzzapp/bin/subprocess/zzz-app-update.sh /opt/zzz/python/bin/subprocess/
dos2unix -q /opt/zzz/python/bin/subprocess/zzz-app-update.sh

#-----misc files that should not be missing-----
for i in \
    /var/log/zzz/ip-logs-rotated \
    /opt/zzz/apache/iptables-allowlist.txt \
    /opt/zzz/apache/os_update_output.txt \
    /etc/iptables/ip-log-accepted.conf \
    /etc/iptables/ip6-log-accepted.conf ; do
    touch $i
    chmod 644 $i
done

#-----added with the new installer-----
touch /opt/zzz/install_part1
touch /opt/zzz/install_part2

#-----rename OS update logfile-----
mv /opt/zzz/apache/yum_output.txt /opt/zzz/apache/os_update_output.txt

#-----install new logrotate config-----
cp $REPOS_DIR/config/logrotated/zzz-iptables /etc/logrotate.d
dos2unix -q /etc/logrotate.d/zzz-iptables

#-----install new iptables/ipset files-----
# subset of commands from 068_setup_iptables.sh
# cp $REPOS_DIR/ /etc/iptables
#EMPTY_SCRIPT=$REPOS_DIR/zzzapp/bash/empty.sh

#-----install ipset allow-ip creator scripts-----
IPTABLES_REPOS_DIR=$REPOS_DIR/config/iptables
IPTABLES_INSTALL_DIR=/etc/iptables
cp $IPTABLES_REPOS_DIR/*.conf $IPTABLES_INSTALL_DIR
cp $IPTABLES_REPOS_DIR/*.sh $IPTABLES_INSTALL_DIR
chmod 755 $IPTABLES_INSTALL_DIR/*.sh
find $IPTABLES_INSTALL_DIR -type f -exec dos2unix -q {} \;

#-----install the main ipset initializer as a netfilter-persistent plugin, then run it-----
NETFILTER_PERSISTENT_PLUGINS=/usr/share/netfilter-persistent/plugins.d
cp $IPTABLES_REPOS_DIR/14-zzz-ipset $NETFILTER_PERSISTENT_PLUGINS
dos2unix -q $NETFILTER_PERSISTENT_PLUGINS/14-zzz-ipset
chmod 755 $NETFILTER_PERSISTENT_PLUGINS/14-zzz-ipset

#-----apache needs to write here-----
chmod 775 /opt/zzz/apache
chown root.www-data /opt/zzz/apache

#-----do the standard upgrade process-----
simple_upgrade_custom_db $CURRENT_VERSION $NEW_VERSION

#-----new ENV vars-----
UBUNTU_CONFIG_DIR=/home/ubuntu/repos/test/config/ubuntu
cp $UBUNTU_CONFIG_DIR/zzz_env_ubuntu /home/ubuntu/
source /home/ubuntu/zzz_env_ubuntu
cp $UBUNTU_CONFIG_DIR/zzz_env_ubuntu /root

#-----jquery 3.6.0-----
/opt/zzz/upgrade/get-jquery.sh

#-----cleanup modules moved into package-----
rm /opt/zzz/python/lib/ZzzTest.py

#-----ubuntu 20 replace default www index file-----
cp /var/www/html/index.htm /var/www/html/index.html

#-----run the ipset create script for allow-ip, but not the other lists, because they are already loaded-----
/etc/iptables/ipset-create-allow-ip.sh

#-----create and install iptables rules-----
/opt/zzz/python/bin/init-iptables.py

#-----rebuild bind configs-----
/opt/zzz/python/bin/build-config.py --bind -q
systemctl restart bind9

#-----rebuild openvpn client configs-----
/opt/zzz/python/bin/build-config.py --openvpn-client -q

#-----install updated openvpn configs-----
/opt/zzz/python/bin/build-config.py --openvpn-server -q
/opt/zzz/python/bin/subprocess/openvpn-restart.sh

#-----rebuild apache configs-----
/opt/zzz/python/bin/build-config.py --apache -q
systemctl restart apache2

#-----run-on-boot service-----
cp $UBUNTU_CONFIG_DIR/zzz-run-on-boot.service /etc/systemd/system
systemctl daemon-reload
systemctl enable zzz-run-on-boot.service

