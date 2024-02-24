#!/bin/bash
#-----upgrade easyrsa from version 3.0.5 to version 3.0.7-----
# github:
#   https://github.com/OpenVPN/easy-rsa.git
#
# This script uses code based on these installer scripts:
#   060_install-easyrsa.sh
#   070_setup-pki.sh
#--------------------------------------------------------------------------------

echo "upgrade-easyrsa.sh - START"

#-----import the config file parser-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid
# vars set in util.sh: REPOS_DIR

SRC_DIR=/home/ubuntu/src
EASYRSA_SRC=$SRC_DIR/easy-rsa
EASYRSA_DIR=`/opt/zzz/python/bin/config-parse.py --var 'Directory/EasyRSA'`

zzzConfig_CA_Default=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/CA/Default'`
zzzConfig_CA_Squid=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/CA/Squid'`

echo "CA default: $zzzConfig_CA_Default"
echo "CA squid: $zzzConfig_CA_Squid"
echo

#-----check if the easyrsa src directory exists-----
if [[ ! -e "$EASYRSA_SRC" ]]; then
    echo "easyrsa src directory not found" 
    exit 1
fi

#TODO: is EasyRSA running already?
# ps -ef|grep easyrsa|grep -v grep

cd $EASYRSA_SRC

#-----update the tag list-----
git fetch

#-----get the latest production version of EasyRSA-----
EASYRSA_LATEST_STABLE_VERSION=`git tag|tail -1`

#-----get the current installed version-----
INSTALLED_VERSION=`grep -P '3\.\d\.\d' $EASYRSA_DIR/ChangeLog | head -1`
INSTALLED_VERSION="v$INSTALLED_VERSION"

#TEST:
echo
echo "EASYRSA_SRC: $EASYRSA_SRC"
echo "INSTALLED_VERSION: $INSTALLED_VERSION"
echo "EASYRSA_LATEST_STABLE_VERSION: $EASYRSA_LATEST_STABLE_VERSION"

echo
echo "Ready to install EasyRSA"
zzz_proceed_or_exit

#-----git checkout-----
echo
git checkout tags/$EASYRSA_LATEST_STABLE_VERSION

#-----verify and install-----
echo "Installing easyrsa..."
cp -rp $EASYRSA_SRC/easyrsa3 /home/ubuntu
cp $EASYRSA_SRC/ChangeLog $EASYRSA_DIR
echo "DONE"
echo


#--------------------------------------------------------------------------------

# NOTE: CA upgrades were for easyrsa versions before 3.0.6, skip the upgrades now

#-----upgrade the CA's-----
#echo "Upgrading CA's..."
#
#cd $EASYRSA_DIR
#
#echo "openvpn/apache CA: $zzzConfig_CA_Default"
#cp vars-openvpn vars
#echo "set_var EASYRSA_REQ_CN \"$zzzConfig_CA_Default\"" >> vars
#./easyrsa upgrade ca
#
#echo
#echo "squid CA: $zzzConfig_CA_Squid"
#cp vars-squid vars
#echo "set_var EASYRSA_REQ_CN \"$zzzConfig_CA_Squid\"" >> vars
#./easyrsa upgrade ca

echo "DONE"
echo
echo "upgrade-easyrsa.sh - END"

