#!/bin/bash

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR, ZZZ_CONFIG_DIR

DATA_DIR=/opt/zzz/data
PYTHON_DIR=/opt/zzz/python

#-----install Zzz tools needed by the Zzz system installer-----

echo "Installing Zzz Tools"

#-----get the subprocess script in place before running it-----
cp $REPOS_DIR/zzzapp/bin/subprocess/* $PYTHON_DIR/bin/subprocess
chmod 755 $PYTHON_DIR/bin/subprocess/*.sh
find $PYTHON_DIR -type f -exec dos2unix -q {} \;

#-----install the old TLD list-----
echo "install the old TLD list"
cp $REPOS_DIR/install/TLD-list.txt $DATA_DIR
chmod 644 $DATA_DIR/TLD-list.txt

#-----install data files-----
for i in \
    country-codes.json \
    country-codes-utf8.json \
    registrars.txt \
    registrar_privacy_services.txt ; do
    cp $REPOS_DIR/src/$i $DATA_DIR
    chmod 644 $DATA_DIR/$i
done

#-----misc files that should not be missing-----
for i in \
    /var/log/zzz/ip-logs-rotated \
    /var/log/zzz/icap/zzz-icap-data \
    /opt/zzz/apache/dns-blacklist.txt \
    /opt/zzz/apache/iptables-allowlist.txt \
    /opt/zzz/apache/iptables-blacklist.txt \
    /opt/zzz/apache/openvpn_version_check.txt \
    /opt/zzz/apache/OS_Updates.txt \
    /opt/zzz/apache/squid_version_check.txt \
    /opt/zzz/apache/zzz_version_check.txt \
    /opt/zzz/apache/os_update_output.txt \
    /opt/zzz/apache/dev/zzz-code-diff.txt \
    /opt/zzz/apache/dev/zzz-installer-output.txt \
    /opt/zzz/apache/dev/zzz-git-branches.txt \
    /opt/zzz/apache/dev/zzz-git-branch-current.txt \
    /opt/zzz/apache/dev/zzz-git-output.txt \
    /opt/zzz/apache/dev/zzz-pytest.txt \
    /opt/zzz/apache/dev/zzz-upgrade.log \
    /opt/zzz/data/hide_ips.txt \
    /etc/iptables/ipset-update-allowlist.conf \
    /etc/iptables/ip-allowlist.conf \
    /etc/iptables/ip-blacklist.conf \
    /etc/iptables/ip-countries.conf \
    /etc/iptables/ip-log-accepted.conf \
    /etc/iptables/ip6-allowlist.conf \
    /etc/iptables/ip6-blacklist.conf \
    /etc/iptables/ip6-countries.conf \
    /etc/iptables/ip6-log-accepted.conf ; do
    touch $i
    chmod 644 $i
done

#-----run the app update (this installs the zzz codebase)-----
# zzz-app-update.sh calls config-parse.py, which loads Config.py, which requires country-codes.json (installed above)
$PYTHON_DIR/bin/subprocess/zzz-app-update.sh

#-----get the ipdeny files-----
/opt/zzz/upgrade/upgrade-ipdeny.sh

#-----files needed by python modules-----
# zzz-app-update.sh populated the ZZZ_CONFIG_DIR dir above
# nobumpsites
SQUID_CONFIG_DIR=$ZZZ_CONFIG_DIR/squid
cp $SQUID_CONFIG_DIR/nobumpsites.acl /etc/squid
# bind settings
NAMED_DIR=$ZZZ_CONFIG_DIR/named
cp $NAMED_DIR/settings/* /etc/bind/settings

echo "$ZZZ_SCRIPTNAME - END"
