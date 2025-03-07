#!/bin/bash

# IPv4 and IPv6
# 39102 - 10.5.0.0/24 - OpenVPN dns + squid w/SSL MITM and ICAP
# 39077 - 10.6.0.0/24 - OpenVPN dns-block
# 39094 - 10.7.0.0/24 - OpenVPN dns + squid w/SSL MITM
# 39066 - 10.8.0.0/24 - OpenVPN unfiltered
# 39055 - 10.9.0.0/24 - OpenVPN unfiltered + squid w/SSL MITM - allows logging without blocking

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_CONFIG_DIR

#-----Install routing configs to enable the server to perform routing-----
cp $ZZZ_CONFIG_DIR/ubuntu/80-zzz-sysctl.conf /etc/sysctl.d

#-----reload system configs-----
# All Configs:
# sysctl --system
/lib/systemd/systemd-sysctl 80-zzz-sysctl.conf

#
# Just the sysctl.conf file:
#sysctl -p

#-----install iptables logging support-----
chmod 755 /var/log/iptables
for i in \
    /var/log/iptables/ipv4.log \
    /var/log/iptables/ipv4-accepted.log \
    /var/log/iptables/ipv4-blocked.log \
    /var/log/iptables/ipv6.log \
    /var/log/iptables/ipv6-accepted.log \
    /var/log/iptables/ipv6-blocked.log ; do
    touch $i
    chown syslog.syslog $i
    chmod 644 $i
done
IPTABLES_LOGGING_CONF=/etc/rsyslog.d/11-iptables.conf
cp $ZZZ_CONFIG_DIR/ubuntu/rsyslog-11-iptables.conf $IPTABLES_LOGGING_CONF
dos2unix -q $IPTABLES_LOGGING_CONF
systemctl restart rsyslog

#-----install ipset/iptables scripts-----
IPTABLES_REPOS_DIR=$ZZZ_CONFIG_DIR/iptables
IPTABLES_INSTALL_DIR=/etc/iptables
#IPSET_UPDATE_BLACKLIST_CONFIG=ipset-update-blacklist.conf
#IPSET_UPDATE_BLACKLIST_SCRIPT=ipset-update-blacklist.sh
#IPSET_BLACKLIST_SCRIPT=ipset-create-blacklist.sh
cp $IPTABLES_REPOS_DIR/*.conf $IPTABLES_INSTALL_DIR
cp $IPTABLES_REPOS_DIR/*.sh $IPTABLES_INSTALL_DIR
chmod 755 $IPTABLES_INSTALL_DIR/*.sh
find $IPTABLES_INSTALL_DIR -type f -exec dos2unix -q {} \;

#--------------------------------------------------------------------------------

#-----IPv6 has separate config files-----
zzzConfig_IPv6_Activate=`/opt/zzz/python/bin/config-parse.py --var 'IPv6/Activate'`
if [[ $zzzConfig_IPv6_Activate == "True" ]]; then
    #-----run the IPv6 setup-----
    $REPOS_DIR/install/setup_ipv6.sh
else
    #-----install empty IPv6 scripts so the netfilter-persistent plugin still works-----
    EMPTY_SCRIPT=$REPOS_DIR/zzzapp/bash/empty.sh
    cp $EMPTY_SCRIPT $IPTABLES_INSTALL_DIR/ipset-ipv6-create-blacklist.sh
    cp $EMPTY_SCRIPT $IPTABLES_INSTALL_DIR/ipset-ipv6-create-countries.sh
    cp $EMPTY_SCRIPT $IPTABLES_INSTALL_DIR/ipset-ipv6-update-blacklist.sh
    cp $EMPTY_SCRIPT $IPTABLES_INSTALL_DIR/ipset-ipv6-update-countries.sh
    #TODO: add allowlist scripts
fi

#--------------------------------------------------------------------------------

#-----install the main ipset initializer as a netfilter-persistent plugin, then run it-----
NETFILTER_PERSISTENT_PLUGINS=/usr/share/netfilter-persistent/plugins.d
cp $IPTABLES_REPOS_DIR/14-zzz-ipset $NETFILTER_PERSISTENT_PLUGINS
dos2unix -q $NETFILTER_PERSISTENT_PLUGINS/14-zzz-ipset
chmod 755 $NETFILTER_PERSISTENT_PLUGINS/14-zzz-ipset
$NETFILTER_PERSISTENT_PLUGINS/14-zzz-ipset start

#-----create and install iptables rules-----
# this also generates /etc/logrotate.d/zzz-iptables from a template
/opt/zzz/python/bin/init-iptables.py

#-----generate ipset configs for each country, so they are ready to install when selected-----
/opt/zzz/python/bin/update-ipset-countries.py

echo "$ZZZ_SCRIPTNAME - END"
