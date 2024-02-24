#!/bin/bash

# download
# compile
# install
# add configs

ZZZ_SCRIPTNAME=`basename "$0"`
echo "$ZZZ_SCRIPTNAME - START"

source /opt/zzz/util/util.sh
# vars set in util.sh: REPOS_DIR

SRC_DIR=/home/ubuntu/src
OPENVPN_SRC=$SRC_DIR/openvpn

#-----get the latest OpenVPN from the official repos on GitHub-----
cd $SRC_DIR
git clone https://github.com/OpenVPN/openvpn.git
cd $OPENVPN_SRC

# OPENVPN_LATEST_STABLE_VERSION=`git tag|grep -v '_'|tail -1`
OPENVPN_LATEST_STABLE_VERSION="v2.6.9"
git checkout tags/$OPENVPN_LATEST_STABLE_VERSION

#-----initialize the Git submodule inside openvpn (required for the compile to work)-----
git submodule update --init --recursive
autoreconf -i

#-----compile and install-----
./configure --enable-systemd
make -j `nproc`
make check
make install

#-----create the TA key-----
# For extra security beyond that provided by SSL/TLS, create an "HMAC firewall" to help block DoS attacks and UDP port flooding.
openvpn --genkey secret ta.key
chown root.root ta.key
chmod 600 ta.key
mv ta.key /etc/openvpn/

#-----install configs-----
#TODO: copy from repos to install locations
# Need a script that takes as inputs:
#   1) a server.conf template
#       file paths: ca, cert, key, dh, tls-auth, askpass
#       DNS IP address
#   2) an install.conf file containing entries for each openvpn server needed:
#       port
#       server class-C IP address
#       ifconfig-pool-persist logfile
#       status logfile
# ...and makes 4 openvpn config files
# Servers:
#   open: server.conf
#       uses direct DNS forwarding to google via BIND
#       no squid
#   DNS-only: server-dns.conf
#       split DNS in BIND:
#           local null zone files for blocked domains
#           forward to google for all others
#   open-squid(logging without blocking): server-squid.conf
#       uses direct DNS forwarding to google via BIND
#       iptables redirect to squid WITHOUT IP-blocking
#   all filters(DNS, iptables, squid logging): server-filtered.conf
#       iptables IP blocking
#       split DNS in BIND

#-----install OpenVPN server configs-----
/opt/zzz/python/bin/build-config.py --openvpn-server -q

#-----re-build all openvpn client files-----
# 070_setup-pki.sh calls init-openvpn-pki.sh
# the client files were built in init-openvpn-pki.sh before ta.key existed
/opt/zzz/python/bin/build-config.py --openvpn-client -q

#-----soft link to fix file path differences between CentOS and Ubuntu-----
#TODO: reference the correct filepath in code so the soft link is not needed
IPP_FILE=/etc/openvpn/server/ipp-filtered.txt
touch $IPP_FILE
chown root.root $IPP_FILE
chmod 644 $IPP_FILE
ln -s $IPP_FILE /etc/openvpn/ipp-filtered.txt

#-----startup OpenVPN servers (auto-creates virtual network interfaces tun0, tun1, ...)-----
systemctl enable openvpn-server@server
systemctl enable openvpn-server@server-dns
systemctl enable openvpn-server@server-icap
systemctl enable openvpn-server@server-filtered
systemctl enable openvpn-server@server-squid
/opt/zzz/python/bin/subprocess/openvpn-start.sh

echo "$ZZZ_SCRIPTNAME - END"
