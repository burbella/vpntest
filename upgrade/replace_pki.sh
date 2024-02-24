#!/bin/bash
#-----Replace the entire PKI setup on the current machine with a new one-----
# Setting up a second VPN server?
# Forgot to change the Host/Domain settings in the zzz.conf to a different domain name?
# iPhones will not allow another root cert to be installed in this case.
# Rather than re-install another machine from scratch, run this to just make a new PKI setup.
#
#--------------------------------------------------------------------------------

#TODO: make an openvpn int-CA in install/070_setup-pki.sh
#      command-line option here to just rebuild openvpn int-CA or zzz root CA also

echo "replace_pki.sh - START"

#-----import the shell utils-----
source /opt/zzz/util/util.sh
exit_if_not_running_as_root
exit_if_configtest_invalid

zzzConfig_Domain=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/Domain'`
zzzConfig_VPNserver=`/opt/zzz/python/bin/config-parse.py --var 'IPv4/VPNserver'`
zzzConfig_VPNusers=`/opt/zzz/python/bin/config-parse.py --var 'VPNusers' --yaml`
zzzConfig_CA_Default=`/opt/zzz/python/bin/config-parse.py --var 'AppInfo/CA/Default'`

# vars set in util: REPOS_DIR, ZZZ_CONFIG_DIR, ZZZ_INSTALLER_DIR
NAMED_DIR=$ZZZ_CONFIG_DIR/named
ZZZ_LOG_DIR=/var/log/zzz

extract_domain_from_subdomain $zzzConfig_Domain

#-----get the server IP's if needed-----
if [[ $zzzConfig_VPNserver == "AUTODETECT" ]]; then
    autodetect_ipv4
    zzzConfig_VPNserver=$ZZZ_AUTODETECT_IPV4
    echo "Autodetected VPNserver IPv4: $zzzConfig_VPNserver"
fi

echo
echo "WARNING: THIS WILL REPLACE YOUR ENTIRE PKI STRUCTURE"
echo "Run this app in 'screen' in case of lost connection."
echo "The VPN will be down for a few minutes while the process completes."
echo "You will get new root certs and new OpenVPN user files."
echo "After it runs, you will need to download and install the files (steps 5 and 6 in INSTALL.txt)"
echo
echo "Here is the config data in /etc/zzz.conf:"
echo "  Domain: $zzzConfig_Domain (apache SSL cert uses this)"
echo "  Extracted Domain: $ZZZ_DOMAIN_EXTRACTED (will replace zzz.zzz zone file)"
echo "  CA Default name: $zzzConfig_CA_Default"
echo "  VPNserver: $zzzConfig_VPNserver (VPN clients connect to this - must be externally available)"
echo "If these are not the new PKI settings, exit this app and update the config file, then run the app again."
echo
echo "VPN users list:"
# not running "build-config.py --openvpn-users" since we don't know if the new users list is approved yet
echo $zzzConfig_VPNusers | tr "," "\n"
echo

zzz_proceed_or_exit

echo "Stopping services: apache, openvpn, squid, zzz ICAP server, zzz daemon"
systemctl stop apache2
systemctl stop squid
systemctl stop squid-icap
systemctl stop zzz
systemctl stop zzz_icap
/opt/zzz/python/bin/subprocess/openvpn-stop.sh

#-----remove old openvpn client files (only matters if the usernames changed in the zzz.conf file)-----
rm /home/ubuntu/openvpn/*

echo
echo "Making new PKI (auto-removes the old PKI)"
$ZZZ_INSTALLER_DIR/070_setup-pki.sh >> $ZZZ_LOG_DIR/replace_pki.log 2>&1

echo
echo "All certs are installed"

echo
echo "Updating apache"
/opt/zzz/python/bin/build-config.py --apache

#-----rebuild the BIND configs and restart BIND-----
echo
echo "Updating BIND"
/opt/zzz/python/bin/build-config.py --bind
#-----add a BIND soft link to fix file-not-found errors-----
if [[ "$ZZZ_DOMAIN_EXTRACTED" != "zzz.zzz" ]]; then
    ZZZ_ZONE_SOFT_LINK=/var/cache/bind/$ZZZ_DOMAIN_EXTRACTED.zone.file
    #-----only do this if the soft link does not exist already-----
    if [[ ! -e "$ZZZ_ZONE_SOFT_LINK" ]]; then
        ln -s /etc/bind/$ZZZ_DOMAIN_EXTRACTED.zone.file $ZZZ_ZONE_SOFT_LINK
    fi
fi
systemctl restart bind9

#-----rebuild the openvpn configs-----
echo "Updating openvpn"
/opt/zzz/python/bin/build-config.py --openvpn-client
/opt/zzz/python/bin/build-config.py --openvpn-server

#-----rebuild the squid config-----
echo "Updating squid"
/opt/zzz/python/bin/build-config.py --squid

#-----this also does a stop/start on squid-----
echo
echo "Clearing squid SSL cache"
/home/ubuntu/bin/squid-clear-cert-cache

echo
echo "Starting services: apache, openvpn, squid"
# restart is more reliable than start with apache2
# sometimes start just fails for some reason
systemctl restart apache2
# no need to start start squid here since the squid-clear-cert-cache script will start it
systemctl start zzz
systemctl start zzz_icap
/opt/zzz/python/bin/subprocess/openvpn-start.sh

echo
echo "DONE Replacing PKI"
echo
echo "Follow steps 6 and 7 in INSTALL.txt to do client cert/config installs"
echo "Step 6: Install VPN client configs on all devices"
echo "Step 7: Download and insert these as Trusted Root Certs on all devices that need the VPN"
echo
USER_INSTRUCTIONS="/opt/zzz/user_instructions.txt"
cat $USER_INSTRUCTIONS

echo
echo "replace_pki.sh - END"
