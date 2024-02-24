#!/bin/bash
# install.sh - main installer script
# Read INSTALL.txt for installation procedures.
# This calls all the other installer scripts in the right order
#   install.sh:
#     install_utils.sh
#       util.sh
#       001
#       005
#       010
#       etc.

REPOS_DIR=/home/ubuntu/repos/vpntest

echo
echo "Zzz Enhanced VPN installer starting . . ."
echo

#-----update the repos installer with the latest list of apps-----
apt-get -y -qq update

#-----dos2unix will be used everywhere, so install it early-----
apt-get -y -qq install dos2unix

#-----install bash utils-----
mkdir -p /opt/zzz/util
for i in \
    install_utils.sh \
    util.sh ; do
    cp $REPOS_DIR/zzzapp/bash/$i /opt/zzz/util
    chmod 644 /opt/zzz/util/$i
    dos2unix -q /opt/zzz/util/$i
done

source /opt/zzz/util/install_utils.sh

#-----install_utils.sh function to expand the installer features without editing this file-----
zzz_full_system_install
